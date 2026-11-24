import json
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Product
from ..schemas import OrderCreate, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/api/orders", tags=["Orders"])


def order_to_schema(o: Order) -> OrderOut:
    """Convert SQLAlchemy Order model to OrderOut schema with parsed JSON fields."""
    try:
        items = json.loads(o.items_json) if o.items_json else []
    except Exception:
        items = []

    try:
        shipping = json.loads(o.shipping_address_json) if o.shipping_address_json else None
    except Exception:
        shipping = None

    try:
        history = json.loads(o.history_json) if o.history_json else []
    except Exception:
        history = []

    return OrderOut(
        id=o.id,
        buyerId=o.buyer_id,
        buyerName=o.buyer_name,
        email=o.email,
        phone=o.phone,
        subtotal=o.subtotal,
        delivery=o.delivery,
        total=o.total,
        paymentMode=o.payment_mode,
        status=o.status,
        items=items,
        shipping=shipping,
        history=history,
        createdAt=o.created_at.isoformat() if isinstance(o.created_at, datetime) else str(o.created_at),
    )


@router.get("", response_model=list[OrderOut], response_model_by_alias=True)
def get_orders(
    buyer_id: int | None = Query(default=None, alias="buyerId"),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """Retrieve all orders, optionally filtered by buyerId or status."""
    stmt = select(Order)
    if buyer_id is not None:
        stmt = stmt.where(Order.buyer_id == buyer_id)
    if status and status.strip():
        stmt = stmt.where(Order.status == status.strip())

    stmt = stmt.order_by(Order.created_at.desc())
    orders = db.scalars(stmt).all()
    return [order_to_schema(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut, response_model_by_alias=True)
def get_order(order_id: str, db: Session = Depends(get_db)):
    """Retrieve a single order by ID."""
    order = db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID '{order_id}' not found",
        )
    return order_to_schema(order)


@router.post("", response_model=OrderOut, response_model_by_alias=True, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    """Place a new order and decrement product stock."""
    now_str = datetime.now(timezone.utc).isoformat()
    today_code = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_suffix = random.randint(1000, 9999)
    order_id = (payload.id or "").strip() or f"SHP-{today_code}-{rand_suffix}"

    items_data = [item.model_dump(by_alias=True) for item in payload.items]
    shipping_data = payload.shipping.model_dump() if payload.shipping else None
    history_data = [{"status": "Placed", "date": now_str}]

    new_order = Order(
        id=order_id,
        buyer_id=payload.buyer_id,
        buyer_name=payload.buyer_name,
        email=payload.email,
        phone=payload.phone,
        subtotal=payload.subtotal,
        delivery=payload.delivery,
        total=payload.total,
        payment_mode=payload.payment_mode,
        status="Placed",
        items_json=json.dumps(items_data),
        shipping_address_json=json.dumps(shipping_data) if shipping_data else None,
        history_json=json.dumps(history_data),
    )
    db.add(new_order)

    # Decrement stock and increment sold count for ordered products
    for item in payload.items:
        prod = db.scalar(select(Product).where(Product.id == item.product_id))
        if prod:
            prod.stock = max(0, prod.stock - item.quantity)
            prod.sold += item.quantity

    db.commit()
    db.refresh(new_order)
    return order_to_schema(new_order)


@router.patch("/{order_id}/status", response_model=OrderOut, response_model_by_alias=True)
def update_order_status(order_id: str, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    """Update order fulfillment status (Placed -> Processing -> Shipped -> Delivered / Cancelled)."""
    order = db.scalar(select(Order).where(Order.id == order_id))
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with ID '{order_id}' not found",
        )

    order.status = payload.status
    try:
        hist = json.loads(order.history_json) if order.history_json else []
    except Exception:
        hist = []

    now_str = datetime.now(timezone.utc).isoformat()
    hist.append({"status": payload.status, "date": now_str})
    order.history_json = json.dumps(hist)

    db.commit()
    db.refresh(order)
    return order_to_schema(order)

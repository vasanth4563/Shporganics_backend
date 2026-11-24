import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order, Product, User, UserRole
from ..schemas import (
    DashboardStatsOut,
    LowStockCard,
    MonthlySalesPoint,
    PendingOrdersCard,
    ProductOut,
    RecentPurchaseOut,
    RegisteredBuyerOut,
    RegisteredBuyersResponse,
    SalesOverviewCard,
    TopSellingCard,
    TotalBuyersCard,
    TotalOrdersCard,
    TotalProductsCard,
    TotalRevenueCard,
    UserOut,
)
from .orders import order_to_schema

router = APIRouter(prefix="/api/seller", tags=["Seller Dashboard APIs"])


def calculate_monthly_sales(db: Session) -> list[MonthlySalesPoint]:
    """Calculate last 6 months of sales dynamically from real orders in the database."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    months = []
    for i in range(5, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        m_label = datetime(year, month, 1).strftime("%b")
        months.append({"year": year, "month_num": month, "month": m_label, "sales": 0.0})

    orders = db.scalars(select(Order)).all()
    for o in orders:
        if o.created_at and o.total:
            for m in months:
                if o.created_at.year == m["year"] and o.created_at.month == m["month_num"]:
                    m["sales"] += float(o.total)

    return [MonthlySalesPoint(month=m["month"], sales=round(m["sales"], 2)) for m in months]


@router.get("/total-revenue", response_model=TotalRevenueCard, response_model_by_alias=True)
def get_total_revenue(db: Session = Depends(get_db)):
    """
    Dedicated API for the 'Total Revenue' card.
    Returns total accumulated revenue across all orders.
    """
    total_rev = db.scalar(select(func.coalesce(func.sum(Order.total), 0.0)))
    val = float(total_rev or 0.0)
    return TotalRevenueCard(
        total_revenue=val,
        currency="INR",
        formatted=f"₹{int(round(val)):,}",
    )


@router.get("/total-products", response_model=TotalProductsCard, response_model_by_alias=True)
def get_total_products(
    include_items: bool = Query(default=True, description="Whether to include product list in response"),
    db: Session = Depends(get_db),
):
    """
    Dedicated API for the 'Total Products' card.
    Returns total count and catalog list of all products.
    """
    count = db.scalar(select(func.count(Product.id))) or 0
    items = db.scalars(select(Product).order_by(Product.name.asc())).all() if include_items else []
    return TotalProductsCard(
        count=int(count),
        products=items,
    )


@router.get("/total-orders", response_model=TotalOrdersCard, response_model_by_alias=True)
def get_total_orders(
    include_orders: bool = Query(default=True, description="Whether to include order records in response"),
    db: Session = Depends(get_db),
):
    """
    Dedicated API for the 'Total Orders' card.
    Returns total order count and list of orders.
    """
    count = db.scalar(select(func.count(Order.id))) or 0
    orders = (
        db.scalars(select(Order).order_by(Order.created_at.desc())).all()
        if include_orders
        else []
    )
    return TotalOrdersCard(
        count=int(count),
        orders=[order_to_schema(o) for o in orders],
    )


@router.get("/stats", response_model=DashboardStatsOut, response_model_by_alias=True)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Combined metrics for all 6 seller dashboard cards:
    - Total Revenue
    - Total Products
    - Total Orders
    - Pending Orders
    - Total Buyers
    - Low Stock Items
    - Top-Selling Products
    - Sales Overview (Monthly Revenue)
    """
    total_rev = db.scalar(select(func.coalesce(func.sum(Order.total), 0.0)))
    total_prods = db.scalar(select(func.count(Product.id)))
    total_orders = db.scalar(select(func.count(Order.id)))
    pending_count = db.scalar(select(func.count(Order.id)).where(Order.status != "Delivered"))
    buyers_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.buyer))
    low_stock_count = db.scalar(select(func.count(Product.id)).where(Product.stock <= 10))

    top_prods = (
        db.scalars(select(Product).order_by(Product.sold.desc()).limit(5)).all()
    )

    return DashboardStatsOut(
        total_revenue=float(total_rev or 0.0),
        total_products=int(total_prods or 0),
        total_orders=int(total_orders or 0),
        pending_orders=int(pending_count or 0),
        total_buyers=int(buyers_count or 0),
        low_stock_items=int(low_stock_count or 0),
        top_selling_products=top_prods,
        monthly_stats=calculate_monthly_sales(db),
    )


@router.get("/pending-orders", response_model=PendingOrdersCard, response_model_by_alias=True)
def get_pending_orders(db: Session = Depends(get_db)):
    """
    Dedicated API for the 'Pending Orders' card.
    Returns count and all orders not yet delivered.
    """
    pending = (
        db.scalars(
            select(Order).where(Order.status != "Delivered").order_by(Order.created_at.desc())
        ).all()
    )
    return PendingOrdersCard(
        count=len(pending),
        orders=[order_to_schema(o) for o in pending],
    )


def build_registered_buyer(u: User, db: Session) -> RegisteredBuyerOut:
    """Helper to assemble a registered buyer with their order history stats."""
    conditions = [(Order.buyer_id == u.id)]
    if u.email:
        conditions.append(func.lower(Order.email) == func.lower(u.email.strip()))
    if u.phone:
        conditions.append(Order.phone == u.phone.strip())
    if u.name:
        conditions.append(func.lower(Order.buyer_name) == func.lower(u.name.strip()))

    orders = db.scalars(
        select(Order)
        .where(or_(*conditions))
        .order_by(Order.created_at.desc())
    ).all()

    total_orders = len(orders)
    total_spent = sum(o.total for o in orders)

    recent_purchase = None
    address = None
    if orders:
        last = orders[0]
        recent_purchase = RecentPurchaseOut(
            id=last.id,
            date=last.created_at.isoformat() if hasattr(last.created_at, "isoformat") else str(last.created_at),
            total=last.total,
            status=last.status,
        )
        if last.shipping_address_json:
            try:
                addr_data = json.loads(last.shipping_address_json)
                if isinstance(addr_data, dict):
                    parts = [
                        addr_data.get("address"),
                        addr_data.get("city"),
                        addr_data.get("state"),
                        addr_data.get("pincode"),
                    ]
                    address = ", ".join(p for p in parts if p)
            except Exception:
                address = None

    return RegisteredBuyerOut(
        id=u.id,
        name=u.name,
        email=u.email,
        phone=u.phone,
        role=u.role,
        is_active=u.is_active,
        created_at=u.created_at.isoformat() if hasattr(u.created_at, "isoformat") else str(u.created_at),
        address=address,
        total_orders=total_orders,
        total_spent=round(total_spent, 2),
        recent_purchase=recent_purchase,
    )


@router.get("/registered-buyers", response_model=RegisteredBuyersResponse, response_model_by_alias=True)
@router.get("/buyers", response_model=RegisteredBuyersResponse, response_model_by_alias=True)
def get_registered_buyers(
    q: str | None = Query(default=None, description="Search filter for buyer name, email, or phone"),
    db: Session = Depends(get_db),
):
    """
    Dedicated API for 'Registered Buyers'.
    Returns customer directory with lifetime order counts, total spent, and recent purchase activity.
    """
    stmt = select(User).where(User.role == UserRole.buyer)
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                User.name.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )

    stmt = stmt.order_by(User.created_at.desc())
    users = db.scalars(stmt).all()
    results = [build_registered_buyer(u, db) for u in users]
    return RegisteredBuyersResponse(count=len(results), buyers=results)


@router.get("/registered-buyers/{buyer_id}", response_model=RegisteredBuyerOut, response_model_by_alias=True)
def get_registered_buyer_by_id(buyer_id: int, db: Session = Depends(get_db)):
    """Retrieve full details of a specific registered buyer including order activity."""
    user = db.scalar(select(User).where((User.id == buyer_id) & (User.role == UserRole.buyer)))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Registered buyer with ID '{buyer_id}' not found",
        )
    return build_registered_buyer(user, db)


@router.get("/total-buyers", response_model=TotalBuyersCard, response_model_by_alias=True)
def get_total_buyers(db: Session = Depends(get_db)):
    """
    Dedicated API for the 'Total Buyers' card.
    Returns count and list of registered buyers.
    """
    buyers = (
        db.scalars(
            select(User).where(User.role == UserRole.buyer).order_by(User.created_at.desc())
        ).all()
    )
    return TotalBuyersCard(
        count=len(buyers),
        buyers=buyers,
    )


@router.get("/low-stock-items", response_model=LowStockCard, response_model_by_alias=True)
def get_low_stock_items(
    threshold: int = Query(default=10, ge=0, description="Threshold below which items are flagged as low stock"),
    db: Session = Depends(get_db),
):
    """
    Dedicated API for the 'Low Stock Items' card.
    Returns count and list of products where stock <= threshold.
    """
    low_stock_prods = (
        db.scalars(
            select(Product).where(Product.stock <= threshold).order_by(Product.stock.asc())
        ).all()
    )
    return LowStockCard(
        count=len(low_stock_prods),
        threshold=threshold,
        products=low_stock_prods,
    )


@router.get("/top-selling", response_model=TopSellingCard, response_model_by_alias=True)
def get_top_selling_products(
    limit: int = Query(default=5, ge=1, le=50, description="Maximum number of top products"),
    db: Session = Depends(get_db),
):
    """
    Dedicated API for the 'Top-Selling Products' card.
    Returns products sorted by units sold descending.
    """
    prods = (
        db.scalars(select(Product).order_by(Product.sold.desc()).limit(limit)).all()
    )
    return TopSellingCard(
        count=len(prods),
        products=prods,
    )


@router.get("/sales-overview", response_model=SalesOverviewCard, response_model_by_alias=True)
def get_sales_overview(db: Session = Depends(get_db)):
    """
    Dedicated API for the 'Sales Overview' card.
    Returns monthly gross revenue figures (INR) for charts.
    """
    total_rev = db.scalar(select(func.coalesce(func.sum(Order.total), 0.0)))
    return SalesOverviewCard(
        total_revenue=float(total_rev or 0.0),
        monthly_stats=calculate_monthly_sales(db),
    )

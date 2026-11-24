from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
import uuid

from ..database import get_db
from ..models import Product
from ..schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("", response_model=list[ProductOut], response_model_by_alias=True)
def get_products(
    category: str | None = Query(default=None, description="Filter by category (podi, snacks, sweets, additional_snacks)"),
    q: str | None = Query(default=None, description="Search term for product name or description"),
    db: Session = Depends(get_db),
):
    """Retrieve all products with optional category filtering and search query."""
    stmt = select(Product)

    if category and category.lower() != "all":
        stmt = stmt.where(Product.category == category.lower())

    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(term),
                Product.description.ilike(term),
                Product.sub_category.ilike(term),
            )
        )

    stmt = stmt.order_by(Product.name.asc())
    return db.scalars(stmt).all()


@router.get("/{product_id}", response_model=ProductOut, response_model_by_alias=True)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """Retrieve a single product by ID."""
    prod = db.scalar(select(Product).where(Product.id == product_id))
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found",
        )
    return prod


@router.post("", response_model=ProductOut, response_model_by_alias=True, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    prod_id = payload.id or f"prod-{uuid.uuid4().hex[:8]}"
    existing = db.scalar(select(Product).where(Product.id == prod_id))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with ID '{prod_id}' already exists",
        )

    prod = Product(
        id=prod_id,
        name=payload.name,
        category=payload.category.lower(),
        sub_category=payload.sub_category,
        description=payload.description,
        price=payload.price,
        discount_price=payload.discount_price,
        stock=payload.stock,
        weight=payload.weight,
        image=payload.image,
        rating=payload.rating,
        sold=payload.sold,
        featured=payload.featured,
        best_seller=payload.best_seller,
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: str, payload: ProductUpdate, db: Session = Depends(get_db)):
    """Update an existing product."""
    prod = db.scalar(select(Product).where(Product.id == product_id))
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found",
        )

    data = payload.model_dump(exclude_unset=True)
    if "category" in data and data["category"]:
        data["category"] = data["category"].lower()

    for field, val in data.items():
        if hasattr(prod, field):
            setattr(prod, field, val)

    db.commit()
    db.refresh(prod)
    return prod


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str, db: Session = Depends(get_db)):
    """Delete a product by ID."""
    prod = db.scalar(select(Product).where(Product.id == product_id))
    if not prod:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found",
        )
    db.delete(prod)
    db.commit()
    return None

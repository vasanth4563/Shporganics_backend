from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.buyer


class LoginRequest(BaseModel):
    email: EmailStr | None = None
    username: str | None = None
    password: str
    role: UserRole | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    role: UserRole
    user_id: int
    user: UserOut


class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=64)
    sub_category: str = Field(alias="subCategory")
    description: str = Field(default="")
    price: float = Field(ge=0)
    discount_price: float = Field(alias="discountPrice", ge=0)
    stock: int = Field(default=50, ge=0)
    weight: str = Field(min_length=1, max_length=50)
    image: str = Field(default="")
    rating: float = Field(default=4.8, ge=0, le=5)
    sold: int = Field(default=0, ge=0)
    featured: bool = False
    best_seller: bool = Field(default=False, alias="bestSeller")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProductCreate(ProductBase):
    id: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    sub_category: str | None = Field(default=None, alias="subCategory")
    description: str | None = None
    price: float | None = None
    discount_price: float | None = Field(default=None, alias="discountPrice")
    stock: int | None = None
    weight: str | None = None
    image: str | None = None
    rating: float | None = None
    sold: int | None = None
    featured: bool | None = None
    best_seller: bool | None = Field(default=None, alias="bestSeller")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProductOut(ProductBase):
    id: str
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Order Schemas
# ---------------------------------------------------------------------------

class OrderItemSchema(BaseModel):
    product_id: str = Field(alias="productId")
    name: str
    price: float
    quantity: int = Field(ge=1)
    image: str = ""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class OrderAddressSchema(BaseModel):
    address: str
    city: str
    state: str
    pincode: str


class OrderHistoryItemSchema(BaseModel):
    status: str
    date: str


class OrderCreate(BaseModel):
    id: str | None = None
    buyer_id: int | None = Field(default=None, alias="buyerId")
    buyer_name: str = Field(alias="buyerName")
    email: str | None = None
    phone: str | None = None
    items: list[OrderItemSchema]
    subtotal: float
    delivery: float = 0.0
    total: float
    payment_mode: str = Field(default="Cash on Delivery", alias="paymentMode")
    shipping: OrderAddressSchema | None = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class OrderOut(BaseModel):
    id: str
    buyer_id: int | None = Field(default=None, alias="buyerId")
    buyer_name: str = Field(alias="buyerName")
    email: str | None = None
    phone: str | None = None
    subtotal: float
    delivery: float
    total: float
    payment_mode: str = Field(alias="paymentMode")
    status: str
    items: list[OrderItemSchema] = []
    shipping: OrderAddressSchema | None = None
    history: list[OrderHistoryItemSchema] = []
    created_at: datetime | str = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Seller Dashboard Metric & Card Schemas
# ---------------------------------------------------------------------------

class MonthlySalesPoint(BaseModel):
    month: str
    sales: float


class TotalRevenueCard(BaseModel):
    total_revenue: float
    currency: str = "INR"
    formatted: str


class TotalProductsCard(BaseModel):
    count: int
    products: list[ProductOut] = []


class TotalOrdersCard(BaseModel):
    count: int
    orders: list[OrderOut] = []


class PendingOrdersCard(BaseModel):
    count: int
    orders: list[OrderOut]


class TotalBuyersCard(BaseModel):
    count: int
    buyers: list[UserOut]


class RecentPurchaseOut(BaseModel):
    id: str
    date: str
    total: float
    status: str


class RegisteredBuyerOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole = UserRole.buyer
    is_active: bool = True
    created_at: datetime | str
    address: str | None = None
    total_orders: int = 0
    total_spent: float = 0.0
    recent_purchase: RecentPurchaseOut | None = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RegisteredBuyersResponse(BaseModel):
    count: int
    buyers: list[RegisteredBuyerOut]


class LowStockCard(BaseModel):
    count: int
    threshold: int
    products: list[ProductOut]


class TopSellingCard(BaseModel):
    count: int
    products: list[ProductOut]


class SalesOverviewCard(BaseModel):
    total_revenue: float
    monthly_stats: list[MonthlySalesPoint]


class DashboardStatsOut(BaseModel):
    total_revenue: float
    total_products: int
    total_orders: int
    pending_orders: int
    total_buyers: int
    low_stock_items: int
    top_selling_products: list[ProductOut]
    monthly_stats: list[MonthlySalesPoint]

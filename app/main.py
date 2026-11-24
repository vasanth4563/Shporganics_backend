import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import Order, Product, User, UserRole
from .routers import auth, orders, products, protected, seller
from .security import hash_password

DEMO_USERS = [
    {"name": "Demo Buyer", "email": "buyer@shp.com", "password": "buyer123", "role": UserRole.buyer},
    {"name": "Demo Seller", "email": "seller@shp.com", "password": "seller123", "role": UserRole.seller},
]


def seed_demo_users() -> None:
    with SessionLocal() as db:
        for u in DEMO_USERS:
            if not db.scalar(select(User).where(User.email == u["email"])):
                db.add(
                    User(
                        name=u["name"],
                        email=u["email"],
                        role=u["role"],
                        hashed_password=hash_password(u["password"]),
                    )
                )
        db.commit()


def seed_products() -> None:
    """Seed the 24 official SHP Organics products into PostgreSQL if empty."""
    json_path = Path(__file__).parent / "data" / "products.json"
    if not json_path.exists():
        return

    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Product))
        if count == 0:
            with open(json_path, "r", encoding="utf-8") as f:
                prods_data = json.load(f)
            for p in prods_data:
                db.add(
                    Product(
                        id=p["id"],
                        name=p["name"],
                        category=p["category"],
                        sub_category=p["subCategory"],
                        description=p["description"],
                        price=float(p["price"]),
                        discount_price=float(p["discountPrice"]),
                        stock=int(p.get("stock", 50)),
                        weight=p["weight"],
                        image=p["image"],
                        rating=float(p.get("rating", 4.8)),
                        sold=int(p.get("sold", 0)),
                        featured=bool(p.get("featured", False)),
                        best_seller=bool(p.get("bestSeller", False)),
                    )
                )
            db.commit()
            print(f"[SUCCESS] Seeded {len(prods_data)} products into database.")


def seed_orders() -> None:
    """Seed initial demo orders into PostgreSQL if empty."""
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(Order))
        if count == 0:
            demo_orders = [
                Order(
                    id="SHP-20261102-4821",
                    buyer_id=1,
                    buyer_name="Ananya Sharma",
                    email="buyer@shp.com",
                    phone="9003219694",
                    subtotal=390.0,
                    delivery=40.0,
                    total=430.0,
                    payment_mode="UPI",
                    status="Shipped",
                    items_json=json.dumps([
                        {"productId": "podi-2", "name": "Idly Podi", "price": 40.0, "quantity": 2, "image": ""},
                        {"productId": "sweet-1", "name": "Badhusha", "price": 350.0, "quantity": 1, "image": ""},
                    ]),
                    shipping_address_json=json.dumps({"address": "12, Lotus Residency", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600040"}),
                    history_json=json.dumps([{"status": "Placed", "date": "2026-11-02T10:00:00Z"}, {"status": "Shipped", "date": "2026-11-03T14:30:00Z"}]),
                ),
                Order(
                    id="SHP-20261101-7740",
                    buyer_id=1,
                    buyer_name="Ananya Sharma",
                    email="buyer@shp.com",
                    phone="9003219694",
                    subtotal=545.0,
                    delivery=0.0,
                    total=545.0,
                    payment_mode="Cash on Delivery",
                    status="Delivered",
                    items_json=json.dumps([
                        {"productId": "snack-2", "name": "Butter Murukku", "price": 380.0, "quantity": 1, "image": ""},
                        {"productId": "add-3", "name": "Murukku", "price": 165.0, "quantity": 1, "image": ""},
                    ]),
                    shipping_address_json=json.dumps({"address": "12, Lotus Residency", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600040"}),
                    history_json=json.dumps([{"status": "Placed", "date": "2026-11-01T09:00:00Z"}, {"status": "Delivered", "date": "2026-11-02T17:00:00Z"}]),
                ),
                Order(
                    id="SHP-20261104-1092",
                    buyer_id=1,
                    buyer_name="Rajesh Kumar",
                    email="rajesh@example.com",
                    phone="9840112233",
                    subtotal=620.0,
                    delivery=0.0,
                    total=620.0,
                    payment_mode="UPI",
                    status="Placed",
                    items_json=json.dumps([
                        {"productId": "sweet-2", "name": "Mysore Pak", "price": 310.0, "quantity": 2, "image": ""},
                    ]),
                    shipping_address_json=json.dumps({"address": "45, Green Avenue", "city": "Bengaluru", "state": "Karnataka", "pincode": "560001"}),
                    history_json=json.dumps([{"status": "Placed", "date": "2026-11-04T11:00:00Z"}]),
                ),
            ]
            db.add_all(demo_orders)
            db.commit()
            print("[SUCCESS] Seeded initial demo orders into database.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        if settings.SEED_DEMO_USERS:
            seed_demo_users()
        print("\n[SUCCESS] Connected to database. Tables initialized (clean production state).\n")
    except Exception as e:
        print("\n" + "=" * 65)
        print("[DATABASE ERROR] Could not connect to PostgreSQL:")
        print(f"  {e}")
        print("\nTo fix this:")
        print("  1. Open backend/.env")
        print("  2. Update the password in DATABASE_URL with your actual PostgreSQL password:")
        print("     DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/shp_organics")
        print("  3. (Optional) Or use SQLite for instant local testing:")
        print("     DATABASE_URL=sqlite:///./shp_organics.db")
        print("=" * 65 + "\n")
        raise e
    yield


app = FastAPI(title="SHP Organics API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(seller.router)
app.include_router(protected.router)


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok"}

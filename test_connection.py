"""Script to test database connection and initialize tables."""

import sys
from sqlalchemy import text
from app.config import settings
from app.database import Base, engine, SessionLocal, ensure_database_exists
from app.models import User, UserRole
from app.security import hash_password


def init_db():
    print(f"Connecting to PostgreSQL as user '{settings.DATABASE_URL.split(':')[1].split('//')[-1]}' ...")

    # Step 1: Ensure target database exists
    ensure_database_exists()

    # Step 2: Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[SUCCESS] PostgreSQL connection established successfully!")
    except Exception as e:
        print(f"[ERROR] Could not connect to database: {e}")
        sys.exit(1)

    # Step 3: Create tables
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("[SUCCESS] Tables created successfully!")

    # Step 4: Seed demo users
    print("Seeding demo accounts...")
    with SessionLocal() as db:
        demos = [
            {"name": "Demo Buyer", "email": "buyer@shp.com", "password": "buyer123", "role": UserRole.buyer},
            {"name": "Demo Seller", "email": "seller@shp.com", "password": "seller123", "role": UserRole.seller},
        ]
        for demo in demos:
            existing = db.query(User).filter(User.email == demo["email"]).first()
            if not existing:
                user = User(
                    name=demo["name"],
                    email=demo["email"],
                    hashed_password=hash_password(demo["password"]),
                    role=demo["role"],
                    is_active=True,
                )
                db.add(user)
                print(f"  + Added {demo['role'].value}: {demo['email']} / {demo['password']}")
            else:
                print(f"  = Exists {demo['role'].value}: {demo['email']}")
        db.commit()

    print("\n[SUCCESS] All setup complete! Now run:")
    print("  python -m uvicorn app.main:app --reload --port 8000\n")


if __name__ == "__main__":
    init_db()

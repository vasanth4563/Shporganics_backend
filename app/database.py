from collections.abc import Generator
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


def ensure_database_exists():
    """Ensure the target PostgreSQL database exists; if not, connect to default 'postgres' db and create it."""
    if not settings.DATABASE_URL.startswith("postgresql"):
        return

    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        clean_url = settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")
        parsed = urlparse(clean_url)
        target_db = parsed.path.lstrip("/")

        if not target_db:
            return

        conn = psycopg2.connect(
            user=parsed.username or "postgres",
            password=parsed.password or "vasanth4563",
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            dbname="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname='{target_db}'")
        if not cur.fetchone():
            print(f">>> Database '{target_db}' does not exist. Creating it automatically...")
            cur.execute(f'CREATE DATABASE "{target_db}"')
            print(f">>> [SUCCESS] Created PostgreSQL database '{target_db}'.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[Note] Could not auto-create database '{target_db}': {e}")


# Automatically ensure PostgreSQL target DB exists
ensure_database_exists()

# Configure engine based on database driver (PostgreSQL or SQLite fallback)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs = {"connect_args": {"check_same_thread": False}} if is_sqlite else {"pool_pre_ping": True}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

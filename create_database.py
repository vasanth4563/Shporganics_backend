"""Helper script to create the 'shp_organics' PostgreSQL database if it does not exist."""

import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_USER = "postgres"
DB_PASS = "vasanth4563"
DB_HOST = "localhost"
DB_PORT = 5432
TARGET_DB = "shp_organics"

def create_shp_organics_db():
    print(f"Connecting to PostgreSQL at {DB_HOST}:{DB_PORT} as user '{DB_USER}'...")

    try:
        # Connect to the default 'postgres' maintenance database
        conn = psycopg2.connect(
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            dbname="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Check if 'shp_organics' exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB}'")
        exists = cur.fetchone()

        if not exists:
            print(f"Creating database '{TARGET_DB}'...")
            cur.execute(f'CREATE DATABASE "{TARGET_DB}"')
            print(f"[SUCCESS] Database '{TARGET_DB}' created successfully!")
        else:
            print(f"[SUCCESS] Database '{TARGET_DB}' already exists and is ready!")

        cur.close()
        conn.close()

        print("\nNow start the FastAPI server with:")
        print("  python -m uvicorn app.main:app --reload --port 8000\n")

    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_shp_organics_db()

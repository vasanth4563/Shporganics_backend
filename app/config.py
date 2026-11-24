from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Can specify either DATABASE_URL or individual DB_* variables
    DATABASE_URL: str = "postgresql+psycopg2://postgres:vasanth4563@localhost:5432/shp_organics"

    DB_TYPE: str | None = None
    DB_HOST: str | None = None
    DB_PORT: int | None = None
    DB_USER: str | None = None
    DB_PASSWORD: str | None = None
    DB_NAME: str | None = None

    JWT_SECRET_KEY: str = "super-secret-key-change-in-production-1234567890"
    JWT_SECRET: str | None = None  # alias for JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    SEED_DEMO_USERS: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def model_post_init(self, __context) -> None:
        # If individual DB fields are provided, build DATABASE_URL
        if self.DB_USER and self.DB_PASSWORD and self.DB_NAME:
            host = self.DB_HOST or "localhost"
            port = self.DB_PORT or 5432
            self.DATABASE_URL = f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{host}:{port}/{self.DB_NAME}"

        # Normalize postgres driver for SQLAlchemy 2.0 + psycopg2
        if self.DATABASE_URL.startswith("postgres://"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
        elif self.DATABASE_URL.startswith("postgresql://") and not self.DATABASE_URL.startswith("postgresql+"):
            self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

        # If JWT_SECRET is provided, use it as JWT_SECRET_KEY
        if self.JWT_SECRET:
            self.JWT_SECRET_KEY = self.JWT_SECRET

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""
Configuration for Auth microservice.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os
import json


class Settings(BaseSettings):
    """Auth service settings."""

    # Application
    APP_NAME: str = "I App Auth Service"
    DEBUG: bool = False

    # Security
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # JWT Keys (RS256)
    JWT_PRIVATE_KEY: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None
    JWT_PRIVATE_KEY_FILE: Optional[str] = None
    JWT_PUBLIC_KEY_FILE: Optional[str] = None
    JWT_KEYS_DIR: str = "keys"
    JWT_KEYS_REQUIRED: bool = False

    # Public base URL for generating absolute URLs
    AUTH_PUBLIC_BASE_URL: Optional[str] = None

    # S3
    BUCKET_NAME: Optional[str] = None
    S3_PREFIX: str = "avatars"
    AWS_REGION: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    # CloudFront (public base URL for serving uploaded files)
    CLOUDFRONT_BASE_URL: Optional[str] = None

    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "i_assistant_auth"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    # Redis (for token blacklisting)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: Optional[str] = None
    REDIS_PORT: Optional[int] = None
    REDIS_DB: Optional[int] = None
    REDIS_PASSWORD: Optional[str] = None

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost",
        "https://aidepartment.net",
        "https://app.aidepartment.net",
        "https://auth.aidepartment.net",
    ]

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Email (for password reset)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    FRONTEND_URL: Optional[str] = "http://localhost:3000"

    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"

    # Monitoring
    ENABLE_METRICS: bool = True
    SENTRY_DSN: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def normalize_redis_url(cls, v, info):
        data = info.data or {}
        redis_url = v

        disable_auth = os.getenv("REDIS_DISABLE_AUTH")
        disable_auth = bool(disable_auth and disable_auth.strip().lower() in {"1", "true", "yes", "on"})

        if isinstance(redis_url, str) and redis_url.strip():
            redis_url = redis_url.strip()
            if disable_auth:
                from urllib.parse import urlsplit, urlunsplit
                parts = urlsplit(redis_url)
                host = parts.hostname or "localhost"
                port = parts.port or 6379
                netloc = f"{host}:{port}"
                return urlunsplit((parts.scheme or "redis", netloc, parts.path or "/0", parts.query, parts.fragment))
            return redis_url

        host = data.get("REDIS_HOST") or os.getenv("REDIS_HOST")
        port = data.get("REDIS_PORT") or os.getenv("REDIS_PORT")
        db = data.get("REDIS_DB") or os.getenv("REDIS_DB")
        password = data.get("REDIS_PASSWORD") or os.getenv("REDIS_PASSWORD")

        host = host or "localhost"
        port = int(port) if port is not None and str(port).strip() else 6379
        db = int(db) if db is not None and str(db).strip() else 0

        if password is not None:
            password = str(password).strip()
        if password:
            return f"redis://:{password}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if str(origin).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in s.split(",") if origin.strip()]
        return v

    def get_database_url(self) -> str:
        """Get database URL, constructing from components if not provided."""
        from urllib.parse import quote_plus

        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql://{self.POSTGRES_USER}:{encoded_password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()

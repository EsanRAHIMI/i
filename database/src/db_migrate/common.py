from __future__ import annotations

import os
from urllib.parse import quote_plus


def get_database_url() -> str:
    """Get database URL from environment variables or config."""
    if os.getenv("DATABASE_URL"):
        return os.getenv("DATABASE_URL")  # type: ignore[return-value]

    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "intelligent_ai_assistant")
    postgres_user = os.getenv("POSTGRES_USER", "postgres")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")

    encoded_password = quote_plus(postgres_password)
    return f"postgresql://{postgres_user}:{encoded_password}@{postgres_host}:{postgres_port}/{postgres_db}"


def get_schema(name: str, default: str) -> str:
    value = os.getenv(name, default)
    # very small hardening: keep schema identifier simple
    safe = "".join(ch for ch in value if ch.isalnum() or ch == "_")
    return safe or default


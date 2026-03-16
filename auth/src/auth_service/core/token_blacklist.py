"""Refresh token blacklist utilities (Redis-backed)."""

from __future__ import annotations

import time
from typing import Optional

import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


def _get_redis_client():
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis unavailable for token blacklist; blacklist disabled", error=str(e))
        return None


_redis_client = None


def blacklist_refresh_jti(jti: str, ttl_seconds: int) -> None:
    global _redis_client
    if not jti:
        return

    if _redis_client is None:
        _redis_client = _get_redis_client()

    if _redis_client is None:
        return

    key = f"bl:refresh:{jti}"
    try:
        _redis_client.setex(key, int(ttl_seconds), "1")
    except Exception as e:
        logger.warning("Failed to blacklist refresh token", error=str(e))


def is_refresh_jti_blacklisted(jti: str) -> bool:
    global _redis_client
    if not jti:
        return False

    if _redis_client is None:
        _redis_client = _get_redis_client()

    if _redis_client is None:
        return False

    key = f"bl:refresh:{jti}"
    try:
        return bool(_redis_client.get(key))
    except Exception as e:
        logger.warning("Failed to read blacklist", error=str(e))
        return False

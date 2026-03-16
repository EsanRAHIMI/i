"""Rate limiting utilities."""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass
from typing import Optional

import structlog

from ..config import settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_after_seconds: int


class InMemoryRateLimiter:
    """Simple in-memory fixed-window rate limiter (fallback if Redis is unavailable)."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = int(limit)
        self.window_seconds = int(window_seconds)
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[int, int]] = {}

    def hit(self, key: str) -> RateLimitResult:
        now = int(time.time())
        window_start = now - (now % self.window_seconds)
        window_end = window_start + self.window_seconds

        with self._lock:
            count, start = self._buckets.get(key, (0, window_start))
            if start != window_start:
                count, start = 0, window_start

            if count >= self.limit:
                return RateLimitResult(False, 0, max(0, window_end - now))

            count += 1
            self._buckets[key] = (count, start)
            remaining = max(0, self.limit - count)
            return RateLimitResult(True, remaining, max(0, window_end - now))


class RedisRateLimiter:
    """Redis-backed fixed-window rate limiter."""

    def __init__(self, redis_client, limit: int, window_seconds: int):
        self.redis = redis_client
        self.limit = int(limit)
        self.window_seconds = int(window_seconds)

    def hit(self, key: str) -> RateLimitResult:
        now = int(time.time())
        window_start = now - (now % self.window_seconds)
        window_end = window_start + self.window_seconds
        redis_key = f"rl:{key}:{window_start}"

        pipe = self.redis.pipeline()
        pipe.incr(redis_key, 1)
        pipe.expire(redis_key, self.window_seconds)
        count, _ = pipe.execute()
        count = int(count)

        if count > self.limit:
            return RateLimitResult(False, 0, max(0, window_end - now))

        remaining = max(0, self.limit - count)
        return RateLimitResult(True, remaining, max(0, window_end - now))


def _get_redis_client():
    try:
        import redis

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Ping to ensure connectivity
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis unavailable for rate limiting; using in-memory limiter", error=str(e))
        return None


_redis_client = None
_in_memory = InMemoryRateLimiter(settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW)


def get_rate_limiter():
    global _redis_client
    if _redis_client is None:
        _redis_client = _get_redis_client()

    if _redis_client is not None:
        return RedisRateLimiter(_redis_client, settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW)

    return _in_memory

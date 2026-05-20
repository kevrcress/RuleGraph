"""Redis sliding-window rate limiter per Section 27. Fails open if Redis is unavailable."""
import logging
import time
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            await _redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable — rate limiting disabled: %s", exc)
            _redis = None
    return _redis


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """
    Returns (allowed, remaining).
    If Redis is unavailable, always returns (True, limit) — fail open.
    Uses a sorted-set sliding window keyed on millisecond timestamps.
    """
    r = await get_redis()
    if r is None:
        return True, limit

    now_ms = int(time.time() * 1000)
    window_start = now_ms - window_seconds * 1000
    rate_key = f"rl:{key}"

    try:
        pipe = r.pipeline()
        pipe.zremrangebyscore(rate_key, "-inf", window_start)
        pipe.zadd(rate_key, {str(now_ms): now_ms})
        pipe.zcard(rate_key)
        pipe.expire(rate_key, window_seconds + 1)
        results = await pipe.execute()
        count = results[2]
        allowed = count <= limit
        remaining = max(0, limit - count)
        return allowed, remaining
    except Exception as exc:
        logger.warning("Rate limit check failed (fail-open): %s", exc)
        return True, limit

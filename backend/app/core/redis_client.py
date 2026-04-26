"""
NirovaAI — Redis Cache
======================
Redis speeds things up by caching expensive operations.
For example: if 100 users ask about dengue symptoms,
we only call Groq LLM once and cache the response.

This is OPTIONAL — the app works fine without Redis.
If Redis is unavailable, we just skip the cache.
"""

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover - optional dependency guard
    aioredis = None
from app.core.config import settings
import logging
import json
import time

log = logging.getLogger(__name__)

# Global Redis client
_redis = None
_local_rate_limits = {}


async def connect_redis():
    """Connect to Redis on startup"""
    global _redis

    try:
        if aioredis is None:
            log.warning("Redis python package is not installed; running without Redis cache.")
            _redis = None
            return

        if settings.UPSTASH_REDIS_URL and settings.UPSTASH_REDIS_TOKEN:
            # Production: Upstash Redis (free tier at upstash.com)
            upstash_url = settings.UPSTASH_REDIS_URL.strip()
            if upstash_url.startswith("https://"):
                upstash_url = "rediss://" + upstash_url[len("https://"):]
                log.info("Normalized UPSTASH_REDIS_URL from https:// to rediss://")
            _redis = aioredis.from_url(
                upstash_url,
                password=settings.UPSTASH_REDIS_TOKEN,
                decode_responses=True
            )
        elif settings.REDIS_URL:
            # Local development: Redis running in Docker
            redis_url = settings.REDIS_URL.strip()
            if redis_url and "://" not in redis_url:
                # Accept host:port format and normalize it for convenience.
                redis_url = f"redis://{redis_url}"
                log.info(f"Normalized REDIS_URL to {redis_url}")
            if not redis_url.startswith(("redis://", "rediss://", "unix://")):
                raise ValueError("Redis URL must start with redis://, rediss://, or unix://")
            _redis = aioredis.from_url(
                redis_url,
                decode_responses=True
            )

        if _redis:
            await _redis.ping()
            log.info("✅ Redis connected")

    except Exception as e:
        # Redis is optional — just log the warning and continue
        log.warning(f"Redis not available (that's okay): {e}")
        _redis = None


async def disconnect_redis():
    """Close Redis connection on shutdown"""
    global _redis
    if _redis:
        await _redis.close()


async def cache_get(key: str):
    """
    Get a cached value.
    Returns None if not found or Redis is down.
    """
    if not _redis:
        return None
    try:
        value = await _redis.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None  # Cache miss is never a fatal error


async def cache_set(key: str, value, ttl_seconds: int = 3600):
    """
    Cache a value for ttl_seconds (default: 1 hour).
    Silently fails if Redis is down.
    """
    if not _redis:
        return
    try:
        await _redis.setex(key, ttl_seconds, json.dumps(value))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Redis cache_set failed for key {key}: {e}")


async def cache_delete(key: str):
    """Remove a key from cache"""
    if not _redis:
        return
    try:
        await _redis.delete(key)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Redis cache_get failed for key {key}: {e}")


async def is_rate_limited(key: str, max_requests: int, window_seconds: int) -> bool:
    """
    Return True if request quota is exceeded within the given window.
    Uses Redis INCR/EXPIRE when available; falls back to local process memory.
    """
    if max_requests <= 0:
        return False

    if _redis:
        try:
            count = await _redis.incr(key)
            if count == 1:
                await _redis.expire(key, window_seconds)
            return count > max_requests
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Redis cache_delete failed for key {key}: {e}")

    now = time.time()
    entry = _local_rate_limits.get(key)

    if not entry or entry["expires_at"] <= now:
        _local_rate_limits[key] = {"count": 1, "expires_at": now + window_seconds}
        return False

    entry["count"] += 1
    return entry["count"] > max_requests


# -- Token Blacklist (for JWT revocation on logout/password change) --

_local_blacklist: dict[str, float] = {}


async def blacklist_token(token_jti: str, expires_in_seconds: int) -> None:
    """Add a token to the blacklist so it cannot be reused after logout."""
    if _redis:
        try:
            await _redis.setex(f"bl:{token_jti}", expires_in_seconds, "1")
            return
        except Exception as e:
            log.warning(f"Redis blacklist_token failed: {e}")

    # Fallback to local memory
    _local_blacklist[token_jti] = time.time() + expires_in_seconds


async def is_token_blacklisted(token_jti: str) -> bool:
    """Check if a token has been revoked."""
    if _redis:
        try:
            result = await _redis.get(f"bl:{token_jti}")
            return result is not None
        except Exception:
            pass

    # Fallback to local memory
    entry = _local_blacklist.get(token_jti)
    if entry is None:
        return False
    if entry <= time.time():
        _local_blacklist.pop(token_jti, None)
        return False
    return True

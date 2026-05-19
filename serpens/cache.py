"""TTL cache: sync (``cached``), async in-process (``acached``), async Redis
(``redis_*``, fails open on ``RedisError``).
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


cache: dict = {}


def cached(cache_name, ttl_in_seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = tuple(args) + tuple(f"{k}={v}" for k, v in kwargs.items())
            bucket = cache.get(cache_name, {})

            if cache_key in bucket and bucket[cache_key]["expires_at"] > datetime.now():
                logger.debug(f"Getting cached value from '{cache_name}:{cache_key}'")
                return bucket[cache_key]["value"]

            result = func(*args, **kwargs)

            cache[cache_name] = bucket
            cache[cache_name][cache_key] = {
                "value": result,
                "expires_at": datetime.now() + timedelta(seconds=ttl_in_seconds),
            }

            return result

        return wrapper

    return decorator


def clear_cache(cache_name):
    logger.debug(f"Cleaning cache entry '{cache_name}'")
    cache.pop(cache_name, None)


_acache: dict = {}


def clear_acache(cache_name: Optional[str] = None) -> None:
    if cache_name is None:
        _acache.clear()
    else:
        _acache.pop(cache_name, None)


def acached(cache_name: str, ttl_seconds: int) -> Callable:
    def decorator(func):
        @wraps(func)
        async def wrapper(_owner: Any, *args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            bucket = _acache.setdefault(cache_name, {})
            entry = bucket.get(key)
            now = time.monotonic()
            if entry is not None and entry["expires_at"] > now:
                return entry["value"]
            value = await func(_owner, *args, **kwargs)
            bucket[key] = {"value": value, "expires_at": now + ttl_seconds}
            return value

        return wrapper

    return decorator


REDIS_DEFAULT_TTL = int(os.getenv("CACHE_TTL", "300"))
REDIS_PREFIX = os.getenv("CACHE_PREFIX", "serpens")

_redis_client: Optional[Redis] = None


async def redis_init(url: Optional[str] = None, **kwargs) -> Redis:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    url = url or os.environ["REDIS_URL"]
    _redis_client = Redis.from_url(url=url, decode_responses=True, **kwargs)
    return _redis_client


async def redis_close() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def redis_get_client() -> Redis:
    if _redis_client is None:
        raise RuntimeError("Redis client is not initialized. Did you call redis_init()?")
    return _redis_client


def _redis_key(key: str) -> str:
    return f"{REDIS_PREFIX}:{key}"


async def _redis_safe_get(key: str) -> Optional[str]:
    try:
        return await redis_get_client().get(_redis_key(key))
    except RedisError as exc:
        logger.warning("cache redis GET failed for %s: %s", key, exc)
        return None


async def _redis_safe_set(key: str, value: str, ttl: int) -> None:
    try:
        await redis_get_client().set(_redis_key(key), value, ex=ttl)
    except RedisError as exc:
        logger.warning("cache redis SET failed for %s: %s", key, exc)


async def _redis_safe_delete(key: str) -> None:
    try:
        await redis_get_client().delete(_redis_key(key))
    except RedisError as exc:
        logger.warning("cache redis DELETE failed for %s: %s", key, exc)


async def redis_get(key: str) -> Any:
    raw = await _redis_safe_get(key)
    return None if raw is None else json.loads(raw)


async def redis_set(key: str, value: Any, ttl: int = REDIS_DEFAULT_TTL) -> None:
    await _redis_safe_set(key, json.dumps(value, default=str), ttl)


async def redis_delete(key: str) -> None:
    await _redis_safe_delete(key)


async def redis_cached_get_or_set(key: str, ttl: int, func: Callable, *args, **kwargs) -> Any:
    raw = await _redis_safe_get(key)
    if raw is not None:
        return json.loads(raw)
    value = await func(*args, **kwargs)
    if value is not None:
        await _redis_safe_set(key, json.dumps(value, default=str), ttl)
    return value


def redis_cached(name: str, ttl: int = REDIS_DEFAULT_TTL):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = [name, *(str(a) for a in args), *(f"{k}={v}" for k, v in kwargs.items())]
            return await redis_cached_get_or_set(":".join(key_parts), ttl, func, *args, **kwargs)

        return wrapper

    return decorator

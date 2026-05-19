"""Async Redis-backed cache: singleton client, helpers and a `cached` decorator.

Operations fail open: if the Redis client raises ``RedisError`` (connection
refused, timeout, host unreachable), the cache behaves as a miss for reads
and a no-op for writes. Callers see ``None`` from ``get`` and their function
still runs through ``cached_get_or_set``. Programming errors (calling
``get`` before ``init``) still propagate as ``RuntimeError``.
"""

import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Optional

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

DEFAULT_TTL = int(os.getenv("CACHE_TTL", "300"))
PREFIX = os.getenv("CACHE_PREFIX", "serpens")

_client: Optional[Redis] = None


async def init(url: Optional[str] = None, **kwargs) -> Redis:
    global _client
    if _client is not None:
        return _client
    url = url or os.environ["REDIS_URL"]
    _client = Redis.from_url(url=url, decode_responses=True, **kwargs)
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_client() -> Redis:
    if _client is None:
        raise RuntimeError("Redis client is not initialized. Did you call init()?")
    return _client


def _key(name: str) -> str:
    return f"{PREFIX}:{name}"


async def _safe_get(key: str) -> Optional[str]:
    try:
        return await get_client().get(_key(key))
    except RedisError as exc:
        logger.warning("cache_async GET failed for %s: %s", key, exc)
        return None


async def _safe_set(key: str, value: str, ttl: int) -> None:
    try:
        await get_client().set(_key(key), value, ex=ttl)
    except RedisError as exc:
        logger.warning("cache_async SET failed for %s: %s", key, exc)


async def _safe_delete(key: str) -> None:
    try:
        await get_client().delete(_key(key))
    except RedisError as exc:
        logger.warning("cache_async DELETE failed for %s: %s", key, exc)


async def get(key: str) -> Any:
    raw = await _safe_get(key)
    return None if raw is None else json.loads(raw)


async def set_(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    await _safe_set(key, json.dumps(value, default=str), ttl)


async def delete(key: str) -> None:
    await _safe_delete(key)


async def cached_get_or_set(key: str, ttl: int, func: Callable, *args, **kwargs) -> Any:
    raw = await _safe_get(key)
    if raw is not None:
        return json.loads(raw)
    value = await func(*args, **kwargs)
    if value is not None:
        await _safe_set(key, json.dumps(value, default=str), ttl)
    return value


def cached(name: str, ttl: int = DEFAULT_TTL):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = [name, *(str(a) for a in args), *(f"{k}={v}" for k, v in kwargs.items())]
            return await cached_get_or_set(":".join(key_parts), ttl, func, *args, **kwargs)

        return wrapper

    return decorator

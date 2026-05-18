"""Async Redis-backed cache: singleton client, helpers and a `cached` decorator."""

import json
import os
from functools import wraps
from typing import Any, Callable, Optional

from redis.asyncio import Redis

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


async def get(key: str) -> Any:
    raw = await get_client().get(_key(key))
    return None if raw is None else json.loads(raw)


async def set_(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    await get_client().set(_key(key), json.dumps(value, default=str), ex=ttl)


async def delete(key: str) -> None:
    await get_client().delete(_key(key))


async def cached_get_or_set(key: str, ttl: int, func: Callable, *args, **kwargs) -> Any:
    raw = await get_client().get(_key(key))
    if raw is not None:
        return json.loads(raw)
    value = await func(*args, **kwargs)
    if value is not None:
        await get_client().set(_key(key), json.dumps(value, default=str), ex=ttl)
    return value


def cached(name: str, ttl: int = DEFAULT_TTL):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key_parts = [name, *(str(a) for a in args), *(f"{k}={v}" for k, v in kwargs.items())]
            return await cached_get_or_set(":".join(key_parts), ttl, func, *args, **kwargs)

        return wrapper

    return decorator

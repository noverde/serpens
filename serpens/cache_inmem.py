"""In-process async TTL cache, bucketed by name.

Lives in the worker process only. Best fit for read-mostly data that
benefits from warm-container reuse within a single Lambda / FastAPI
instance. For cross-process / cross-instance caching, use
``serpens.cache_async`` (Redis).

The decorator drops the first positional argument when building the key,
on the assumption it is the bound ``self``/``owner`` (a repository or
service object that points at the same underlying store). Different
instances pointing at the same store therefore hit the same entry.
"""

import time
from functools import wraps
from typing import Any, Callable, Optional

_cache: dict = {}


def clear_cache(name: Optional[str] = None) -> None:
    if name is None:
        _cache.clear()
    else:
        _cache.pop(name, None)


def cached(name: str, ttl_seconds: int) -> Callable:
    def decorator(func):
        @wraps(func)
        async def wrapper(_owner: Any, *args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            bucket = _cache.setdefault(name, {})
            entry = bucket.get(key)
            now = time.monotonic()
            if entry is not None and entry["expires_at"] > now:
                return entry["value"]
            value = await func(_owner, *args, **kwargs)
            bucket[key] = {"value": value, "expires_at": now + ttl_seconds}
            return value

        return wrapper

    return decorator

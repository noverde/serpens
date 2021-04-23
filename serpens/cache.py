import logging
from functools import wraps
from datetime import datetime, timedelta


cache = {}

logger = logging.getLogger(__name__)


def cached(cache_name, ttl_in_seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = tuple(args) + tuple(f"{k}={v}" for k, v in kwargs.items())
            cached = cache.get(cache_name, {})

            if cache_key in cached and cached[cache_key]["expires_at"] > datetime.now():
                logger.debug(f"Getting cached value from '{cache_name}:{cache_key}'")
                return cached[cache_key]["value"]

            result = func(*args, **kwargs)

            cache[cache_name] = cached
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

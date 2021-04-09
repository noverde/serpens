import logging
from functools import wraps
from datetime import datetime, timedelta


cache = {}

logger = logging.getLogger(__name__)


def cached(cache_name, ttl_in_seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = tuple(args) + tuple(kwargs)
            cached = cache.get(cache_name, {})
            if cache_key in cached and cached[cache_key]["expires_at"] > datetime.now():
                print("got from cache")
                logger.debug(f"Getting value with key {cache_key} from cache {cache_name}")
                return cached[cache_key]
            print("calling function")
            result = func(*args, **kwargs)
            cache[cache_name] = cached
            cache[cache_name][cache_key] = {
                "value": result,
                "expires_at": datetime.now() + timedelta(seconds=ttl_in_seconds)
            }
            return result
        return wrapper
    
    return decorator


def clear_cache(cache_name):
    logger.debug(f"Cleaning cache with name {cache_name}")
    cache[cache_name] = {}

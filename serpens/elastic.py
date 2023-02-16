import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)

try:
    import elasticapm
except ImportError:
    logger.warning("Unable to import elasticapm")


def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "ELASTIC_APM_SECRET_TOKEN" in os.environ:
            return elasticapm.capture_serverless(func)(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper

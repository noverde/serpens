import os
import logging
from functools import wraps

from serpens import initializers

initializers.setup()
logger = logging.getLogger(__name__)

try:
    import elasticapm
except ImportError:
    logger.warning("Unable to import elasticapm, make sure there is a version installed")

env = {"development": "dev", "staging": "uat", "production": "production"}


def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "ELASTIC_APM_SECRET_TOKEN" in os.environ:
            environment = os.getenv("ENVIRONMENT", "development")
            os.environ["ELASTIC_APM_ENVIRONMENT"] = env.get(environment, "development")
            return elasticapm.capture_serverless(func)(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper

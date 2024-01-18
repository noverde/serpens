import logging
import sys
import os
from functools import wraps

ELASTIC_APM_ENABLED = "ELASTIC_APM_SECRET_TOKEN" in os.environ
ELASTIC_APM_CAPTURE_BODY = os.getenv("ELASTIC_APM_CAPTURE_BODY") in ("all", "transactions")

logger = logging.getLogger(__name__)

try:
    import elasticapm
except ImportError:
    logger.warning("Unable to import elasticapm")


def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if ELASTIC_APM_ENABLED:
            return elasticapm.capture_serverless(func)(*args, **kwargs)

        return func(*args, **kwargs)

    return wrapper


def capture_exception(exception, is_http_request=False):
    if not ELASTIC_APM_ENABLED:
        return None

    elasticapm.get_client().capture_exception(exc_info=sys.exc_info(), handled=False)

    if is_http_request:
        elasticapm.set_transaction_result("HTTP 5xx", override=False)
        elasticapm.set_transaction_outcome(http_status_code=500, override=False)
        elasticapm.set_context({"status_code": 500}, "response")
    else:
        elasticapm.set_transaction_result("failure", override=False)
        elasticapm.set_transaction_outcome(outcome="failure", override=False)


def capture_response(response):
    if not ELASTIC_APM_ENABLED or not ELASTIC_APM_CAPTURE_BODY:
        return None

    elasticapm.set_custom_context({"response_body": response})


def set_transaction_result(result, override=True):
    if ELASTIC_APM_ENABLED:
        elasticapm.set_transaction_result(result, override=override)


def setup():
    if not ELASTIC_APM_ENABLED or not ELASTIC_APM_CAPTURE_BODY:
        return None

    if "ELASTIC_APM_PROCESSORS" not in os.environ:
        os.environ["ELASTIC_APM_PROCESSORS"] = (
            "serpens.elastic_sanitize.sanitize_http_request_body,"
            "serpens.elastic_sanitize.sanitize_http_response_body,"
            "elasticapm.processors.sanitize_stacktrace_locals,"
            "elasticapm.processors.sanitize_http_request_cookies,"
            "elasticapm.processors.sanitize_http_headers,"
            "elasticapm.processors.sanitize_http_wsgi_env,"
            "elasticapm.processors.sanitize_http_request_body"
        )

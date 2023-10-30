import json
import logging
import sys
import os
from functools import wraps
from serpens.schema import SchemaEncoder

logger = logging.getLogger(__name__)

try:
    import elasticapm
    from elasticapm.utils import starmatch_to_regex
    from elasticapm.processors import MASK, varmap
except ImportError:
    logger.warning("Unable to import elasticapm")


def _get_response_sanitize_fields(enabled):
    if not enabled:
        return None

    field_names = None
    if "ELASTIC_APM_RESPONSE_SANITIZE_FIELD_NAMES" in os.environ:
        field_names = os.environ["ELASTIC_APM_RESPONSE_SANITIZE_FIELD_NAMES"].split(",")
    else:
        field_names = (
            "password",
            "passwd",
            "pwd",
            "secret",
            "*key",
            "*token*",
            "*session*",
            "*credit*",
            "*card*",
            "*auth*",
        )

    return [starmatch_to_regex(x) for x in field_names]


ELASTIC_APM_ENABLED = "ELASTIC_APM_SECRET_TOKEN" in os.environ

ELASTIC_APM_RESPONSE_SANITIZE_FIELDS = _get_response_sanitize_fields(ELASTIC_APM_ENABLED)


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


def _sanitize_var(key, value, sanitize_field_names):
    if value is None:
        return None

    if not key or isinstance(value, dict):
        return value

    key = key.lower().strip()
    for field in sanitize_field_names:
        if field.match(key):
            return MASK

    return value


def capture_response(response):
    if not ELASTIC_APM_ENABLED:
        return None

    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            return None

    if not isinstance(response, (dict, list)):
        return None

    response_body = json.dumps(
        varmap(_sanitize_var, response, sanitize_field_names=ELASTIC_APM_RESPONSE_SANITIZE_FIELDS),
        cls=SchemaEncoder,
    )
    elasticapm.set_custom_context({"response_body": response_body})


def set_transaction_result(result, override=True):
    if ELASTIC_APM_ENABLED:
        elasticapm.set_transaction_result(result, override=override)


def setup():
    if not ELASTIC_APM_ENABLED:
        return None

    os.environ["ELASTIC_APM_PROCESSORS"] = (
        "serpens.elastic_sanitize.sanitize,"
        "elasticapm.processors.sanitize_stacktrace_locals,"
        "elasticapm.processors.sanitize_http_request_cookies,"
        "elasticapm.processors.sanitize_http_headers,"
        "elasticapm.processors.sanitize_http_wsgi_env,"
        "elasticapm.processors.sanitize_http_request_body"
    )

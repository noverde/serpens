import json
import logging
import sys
import os
from functools import wraps
from schema import SchemaEncoder
from serpens import envvars

logger = logging.getLogger(__name__)

_response_sanitize_fields = []

try:
    import elasticapm
    from elasticapm.utils import starmatch_to_regex
    from elastic_sanitize import sanitize_body
except ImportError:
    logger.warning("Unable to import elasticapm")


def elastic_enabled():
    return "ELASTIC_APM_SECRET_TOKEN" in os.environ


def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if elastic_enabled():
            return elasticapm.capture_serverless(func)(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


def capture_exception(exception, is_http_request=False):
    if elastic_enabled():
        elasticapm.get_client().capture_exception(exc_info=sys.exc_info(), handled=False)

        if is_http_request:
            elasticapm.set_transaction_result("HTTP 5xx", override=False)
            elasticapm.set_transaction_outcome(http_status_code=500, override=False)
            elasticapm.set_context({"status_code": 500}, "response")
        else:
            elasticapm.set_transaction_result("failure", override=False)
            elasticapm.set_transaction_outcome(outcome="failure", override=False)


def capture_response(response):
    if not elastic_enabled():
        return None

    if isinstance(response, str) and (response[0] == "{" or response[0] == "["):
        try:
            response = json.loads(response)
        except ValueError:
            pass

    if not isinstance(response, (dict, list)):
        return None

    response_body = json.dumps(
        sanitize_body(response, _response_sanitize_fields), cls=SchemaEncoder
    )
    elasticapm.set_custom_context({"response_body": response_body})


def set_transaction_result(result, override=True):
    if elastic_enabled():
        elasticapm.set_transaction_result(result, override=override)


def setup():
    global _response_sanitize_fields

    if not elastic_enabled():
        return None

    os.environ["ELASTIC_APM_SECRET_TOKEN"] = envvars.get("ELASTIC_APM_SECRET_TOKEN")

    os.environ["ELASTIC_APM_PROCESSORS"] = (
        "serpens.elastic_sanitize.sanitize,"
        "elasticapm.processors.sanitize_stacktrace_locals,"
        "elasticapm.processors.sanitize_http_request_cookies,"
        "elasticapm.processors.sanitize_http_headers,"
        "elasticapm.processors.sanitize_http_wsgi_env,"
        "elasticapm.processors.sanitize_http_request_body"
    )

    sanitize_field_names = None
    if "SERPENS_RESPONSE_SANITIZE_FIELD_NAMES" in os.environ:
        sanitize_field_names = os.environ["SERPENS_RESPONSE_SANITIZE_FIELD_NAMES"].split(",")
    else:
        sanitize_field_names = (
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

    _response_sanitize_fields = [starmatch_to_regex(x) for x in sanitize_field_names]

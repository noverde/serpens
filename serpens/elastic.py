import sys
import os
import logging
from functools import wraps
from serpens import envvars

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


def capture_exception(exception, is_http_request=False):
    if "ELASTIC_APM_SECRET_TOKEN" in os.environ:
        elasticapm.get_client().capture_exception(exc_info=sys.exc_info(), handled=False)

        if is_http_request:
            elasticapm.set_transaction_result("HTTP 5xx", override=False)
            elasticapm.set_transaction_outcome(http_status_code=500, override=False)
            elasticapm.set_context({"status_code": 500}, "response")
        else:
            elasticapm.set_transaction_result("failure", override=False)
            elasticapm.set_transaction_outcome(outcome="failure", override=False)


def set_transaction_result(result, override=True):
    if "ELASTIC_APM_SECRET_TOKEN" in os.environ:
        elasticapm.set_transaction_result(result, override=override)


def _setup_sanitize():
    os.environ["ELASTIC_APM_PROCESSORS"] = (
        "serpens.elastic_sanitize.sanitize,"
        "elasticapm.processors.sanitize_stacktrace_locals,"
        "elasticapm.processors.sanitize_http_request_cookies,"
        "elasticapm.processors.sanitize_http_headers,"
        "elasticapm.processors.sanitize_http_wsgi_env,"
        "elasticapm.processors.sanitize_http_request_body"
    )

    if "ELASTIC_APM_SANITIZE_FIELD_NAMES" in os.environ:
        field_names = os.environ["ELASTIC_APM_SANITIZE_FIELD_NAMES"]
    else:
        field_names = (
            "password,"
            "passwd,"
            "pwd,"
            "secret,"
            "*key,"
            "*token*,"
            "*session*,"
            "*credit*,"
            "*card*,"
            "*auth*,"
            "set-cookie,"
            "document,"
            "cpf"
        )

    if "SERPENS_EXTRA_SANATIZE_FIELD_NAMES" in os.environ:
        field_names = f"{field_names},{os.environ['SERPENS_EXTRA_SANATIZE_FIELD_NAMES']}"

    os.environ["ELASTIC_APM_SANITIZE_FIELD_NAMES"] = field_names


def setup():
    if "ELASTIC_APM_SECRET_TOKEN" in os.environ:
        os.environ["ELASTIC_APM_SECRET_TOKEN"] = envvars.get("ELASTIC_APM_SECRET_TOKEN")

    _setup_sanitize()

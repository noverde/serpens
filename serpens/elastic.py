from enum import Enum
import elasticapm
from serpens import envvars
import os


class EnvironmentType(Enum):
    development = "dev"
    staging = "uat"
    production = "production"


def setup() -> None:

    environment = envvars.get("ENVIRONMENT", "development")

    service_name = envvars.get("AWS_LAMBDA_FUNCTION_NAME", "teste").split("-development")[0]

    elasticapm.Client(
        {
            "service_name": service_name,
            "server_url": envvars.get("ELASTIC_APM_SERVER_URL"),
            "environment": EnvironmentType[environment].value,
            "secret_token": envvars.get("ELASTIC_APM_SECRET_TOKEN"),
        }
    )
    elasticapm.instrumentation.control.instrument()


from elasticapm import capture_serverless  # , get_client


def apply_elk_logger(func):
    def wrapper(*args, **kwargs):
        if os.get("ELASTIC_APM_SERVER_URL") and os.get("ELASTIC_APM_SECRET_TOKEN"):
            return capture_serverless(func)(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper

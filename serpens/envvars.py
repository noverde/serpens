import os

from serpens import parameters
from serpens import secrets


def get(key, default=None):
    result = os.getenv(key, default)

    if result.startswith("parameters://"):
        tmp = result.split("://")[1]
        return parameters.get(tmp)

    if result.startswith("secrets://"):
        tmp = result.split("://")[1].split("?")
        return secrets.get(tmp[0], tmp[1])

    return result

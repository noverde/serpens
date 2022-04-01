import json

import boto3

from serpens.cache import cached


@cached("secrets_manager", 900)
def get(secret_id, keyname=None):
    client = boto3.client("secretsmanager")

    secret_param = client.get_secret_value(SecretId=secret_id)
    secret_value = secret_param["SecretString"]
    try:
        result = json.loads(secret_value)
        if keyname:
            return result[keyname]
        return result
    except json.JSONDecodeError:
        return secret_value

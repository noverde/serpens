import json
from json import JSONDecodeError

import boto3


def get(secret_id, keyname=None):
    client = boto3.client("secretsmanager")
    secret_value = client.get_secret_value(SecretId=secret_id)
    secret = secret_value["SecretString"]
    try:
        result = json.loads(secret)
        if keyname:
            return result["keyname"]
        return result
    except JSONDecodeError:
        return secret

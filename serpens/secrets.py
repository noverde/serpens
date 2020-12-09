import json
from json import JSONDecodeError

import boto3


def get(secret_id):
    client = boto3.client("secretsmanager")
    secret_value = client.get_secret_value(SecretId=secret_id)
    secret = secret_value["SecretString"]
    try:
        return json.loads(secret)
    except JSONDecodeError:
        return secret

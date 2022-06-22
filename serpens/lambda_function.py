import json
from typing import Dict, Optional
import boto3


def invoke(name: str, payload: Dict) -> Optional[Dict]:
    client = boto3.client("lambda")

    response = client.invoke(FunctionName=name, Payload=json.dumps(payload))
    payload = json.loads(response["Payload"].read())

    if 400 <= response["StatusCode"] < 600:
        raise Exception(payload)

    return payload

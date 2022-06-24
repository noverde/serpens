import json
from typing import Any, Dict, Optional
import boto3


def invoke(name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    client = boto3.client("lambda")

    response = client.invoke(FunctionName=name, Payload=json.dumps(payload))
    payload = json.loads(response["Payload"].read())

    if 400 <= response["StatusCode"] < 600:
        raise Exception(payload)

    return payload

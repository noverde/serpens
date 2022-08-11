import json
from typing import Any, Dict
import boto3


def invoke(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    client = boto3.client("lambda")

    response = client.invoke(FunctionName=name, Payload=json.dumps(payload))

    return {
        "status_code": response["StatusCode"],
        "error": response.get("FunctionError"),
        "payload": response["Payload"].read().decode(),
    }

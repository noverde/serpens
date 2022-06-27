import json
from typing import Any, Dict, Optional
import boto3


def invoke(name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    client = boto3.client("lambda")

    return client.invoke(FunctionName=name, Payload=json.dumps(payload))

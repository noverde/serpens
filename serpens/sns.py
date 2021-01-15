import json
from datetime import datetime
from uuid import uuid4

import boto3

from serpens import envvars


def publish_message(category, event_type, aggregate_id, payload):

    AWS_REGION = envvars.get("AWS_REGION")
    AWS_ACCOUNT_ID = envvars.get("AWS_ACCOUNT_ID")
    NOVERDE_EVENTS = envvars.get("NOVERDE_EVENTS")

    sns_client = boto3.client("sns")

    arn = f"arn:aws:sns:{AWS_REGION}:{AWS_ACCOUNT_ID}:{NOVERDE_EVENTS}"
    message = {
        "default": json.dumps(
            {
                "id": str(uuid4()),
                "category": category,
                "type": event_type,
                "at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "aggregate_id": aggregate_id,
                "version": "1.0",
                "payload": payload,
            }
        )
    }

    response = sns_client.publish(
        TargetArn=arn,
        Message=json.dumps(message),
        MessageStructure="json",
        MessageAttributes={
            "event_type": {"DataType": "String", "StringValue": event_type}
        },
    )

    return response

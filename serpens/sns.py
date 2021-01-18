import json
from datetime import datetime
from uuid import uuid4

import boto3


def publish_message(topic_arn, message, attributes={}):
    sns_client = boto3.client("sns")
    response = sns_client.publish(
        TargetArn=topic_arn,
        Message=json.dumps(message),
        MessageStructure="json",
        MessageAttributes=attributes,
    )
    return response


def build_event_message(category, event_type, aggregate_id, payload):
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

    attributes = {
        "event_type": {"DataType": "String", "StringValue": event_type}
    }

    return message, attributes

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

import boto3

from serpens.schema import SchemaEncoder


def publish_message(topic_arn, message, attributes={}):
    sns_client = boto3.client("sns")

    return sns_client.publish(
        TargetArn=topic_arn,
        Message=json.dumps(message),
        MessageStructure="json",
        MessageAttributes=attributes,
    )


@dataclass
class NoverdeEvents:
    category: str
    type: str
    aggregate_id: str
    payload: dict
    id: UUID = field(default_factory=uuid4)
    at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0"

    @property
    def message(self):
        return {"default": json.dumps(asdict(self), cls=SchemaEncoder)}

    @property
    def attributes(self):
        return {"event_type": {"DataType": "String", "StringValue": self.type}}

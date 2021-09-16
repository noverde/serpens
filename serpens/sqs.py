import boto3
import logging
import json

from json.decoder import JSONDecodeError
from uuid import UUID
from typing import Union
from dataclasses import dataclass
from functools import wraps
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def publish_message(queue_url, body, message_group_id=None):
    client = boto3.client("sqs")
    params = {"QueueUrl": queue_url, "MessageBody": body}

    if queue_url.endswith(".fifo"):
        params["MessageGroupId"] = message_group_id
        params["MessageDeduplicationId"] = message_group_id

    return client.send_message(**params)


def handler(func):
    @wraps(func)
    def wrapper(event: dict, context: dict):
        logger.debug(f"Received data: {event}")

        for data in event["Records"]:
            func(Record(data))

    return wrapper


class Attributes:
    SenderId: str
    data: Dict[Any, Any]

    def __init__(self, data: Dict[Any, Any]):
        self.data = data
        self.SenderId = data.get("SenderId")

    @property
    def ApproximateReceiveCount(self) -> int:
        approximate_receive_count = self.data.get("ApproximateReceiveCount")

        if approximate_receive_count:
            return int(approximate_receive_count)
        return approximate_receive_count

    @property
    def SentTimestamp(self):
        sent_timestamp = self.data["SentTimestamp"]

        return datetime.fromtimestamp(float(sent_timestamp) / 1000.0)

    @property
    def ApproximateFirstReceiveTimestamp(self):
        approximate_first_receive_timestamp = self.data["ApproximateFirstReceiveTimestamp"]

        return datetime.fromtimestamp(float(approximate_first_receive_timestamp) / 1000.0)


@dataclass
class EventSourceArn:
    raw: str

    @property
    def queue_name(self):
        if self.raw:
            return self.raw.split(":")[-1]


class Record:
    data: Dict[Any, Any]
    messageId: UUID
    receiptHandle: str
    attributes: Attributes
    md5OfMessageAttributes: str
    md5OfBody: str
    eventSource: str
    eventSourceARN: EventSourceArn
    awsRegion: str

    def __init__(self, data: Dict[Any, Any]):
        self.data = data
        raw_attrs = data.get("attributes", {})

        attrs = Attributes(raw_attrs)
        self.attributes = attrs

        self.messageId = data.get("messageId")
        self.receiptHandle = data.get("receiptHandle")
        self.md5OfMessageAttributes = data.get("md5OfMessageAttributes")
        self.md5OfBody = data.get("md5OfBody")
        self.eventSource = data.get("eventSource")
        self.eventSourceARN = EventSourceArn(data.get("eventSourceARN", ""))
        self.awsRegion = data.get("awsRegion")

    @property
    def messageAttributes(self):
        message_attributes = self.data.get("messageAttributes")

        if message_attributes and isinstance(message_attributes, str):
            return json.loads(message_attributes)
        return message_attributes

    @property
    def body(self) -> Union[dict, str]:
        body_raw = self.data.get("body")

        try:
            return json.loads(body_raw)

        except JSONDecodeError:
            return body_raw

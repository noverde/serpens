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
    sender_id: str

    def __init__(self, data: Dict[Any, Any]):
        self.sender_id = data.get("SenderId")
        self._approximate_receive_count = data.get("ApproximateReceiveCount")
        self._sent_timestamp = data.get("SentTimestamp")
        self._approximate_first_receive_timestamp = data.get("ApproximateFirstReceiveTimestamp")

    @property
    def approximate_receive_count(self) -> int:
        if self._approximate_receive_count:
            return int(self._approximate_receive_count)
        return self._approximate_receive_count

    @property
    def sent_timestamp(self):
        return datetime.fromtimestamp(float(self._sent_timestamp) / 1000.0)

    @property
    def approximate_first_receive_timestamp(self):
        return datetime.fromtimestamp(float(self._approximate_first_receive_timestamp) / 1000.0)


@dataclass
class EventSourceArn:
    raw: str

    @property
    def queue_name(self):
        if self.raw:
            return self.raw.split(":")[-1]


class Record:
    data: Dict[Any, Any]
    message_id: UUID
    receipt_handle: str
    attributes: Attributes
    md5_of_message_attributes: str
    md5_of_body: str
    event_source: str
    event_source_arn: EventSourceArn
    aws_region: str

    def __init__(self, data: Dict[Any, Any]):
        self.data = data
        raw_attrs = data.get("attributes", {})

        attrs = Attributes(raw_attrs)
        self.attributes = attrs

        self.message_id = data.get("messageId")
        self.receipt_handle = data.get("receiptHandle")
        self.md5_of_message_attributes = data.get("md5OfMessageAttributes")
        self.md5_of_body = data.get("md5OfBody")
        self.event_source = data.get("eventSource")
        self.event_source_arn = EventSourceArn(data.get("eventSourceARN"))
        self.aws_region = data.get("awsRegion")

        self._body = data.get("body")
        self._message_attributes = data.get("messageAttributes")

    @property
    def message_attributes(self):
        if self._message_attributes and isinstance(self._message_attributes, str):
            return json.loads(self._message_attributes)
        return self._message_attributes

    @property
    def body(self) -> Union[dict, str]:
        try:
            return json.loads(self._body)

        except JSONDecodeError:
            return self._body

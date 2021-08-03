import boto3
import logging
import json

from json.decoder import JSONDecodeError
from uuid import UUID
from typing import Union
from dataclasses import dataclass
from functools import wraps
from datetime import datetime

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

        for record_raw in event["Records"]:
            raw_attrs = record_raw.get("attributes", None)
            attrs = None

            if raw_attrs:
                attrs = Attributes(
                    approximate_receive_count=raw_attrs.get("ApproximateReceiveCount", None),
                    sent_timestamp=raw_attrs.get("SentTimestamp", None),
                    sender_id=raw_attrs.get("SenderId", None),
                    approximate_first_receive_timestamp=raw_attrs.get(
                        "ApproximateFirstReceiveTimestamp", None
                    ),
                )

            record = Record(
                message_id=record_raw.get("messageId", None),
                receipt_handle=record_raw.get("receiptHandle", None),
                body=record_raw.get("body", None),
                attributes=attrs,
                message_attributes=record_raw.get("messageAttributes", None),
                md5_of_message_attributes=record_raw.get("md5OfMessageAttributes", None),
                md5_of_body=record_raw.get("md5OfBody", None),
                event_source=record_raw.get("eventSource", None),
                event_source_arn=EventSourceArn(record_raw.get("eventSourceARN", None)),
                aws_region=record_raw.get("awsRegion", None),
            )
            func(record)

    return wrapper


@dataclass
class Attributes:
    approximate_receive_count: int
    sent_timestamp: datetime
    sender_id: str
    approximate_first_receive_timestamp: datetime

    def __post_init__(self):
        self.sent_timestamp = datetime.fromtimestamp(float(self.sent_timestamp) / 1000.0)
        self.approximate_first_receive_timestamp = datetime.fromtimestamp(
            float(self.approximate_first_receive_timestamp) / 1000.0
        )
        self.approximate_receive_count = int(self.approximate_receive_count)


@dataclass
class EventSourceArn:
    raw: str

    @property
    def queue_name(self):
        if self.raw:
            return self.raw.split(":")[-1]


@dataclass
class Record:
    message_id: UUID
    receipt_handle: str
    body: Union[str, dict]
    attributes: Attributes
    message_attributes: dict
    md5_of_message_attributes: str
    md5_of_body: str
    event_source: str
    event_source_arn: EventSourceArn
    aws_region: str

    def __post_init__(self):
        if self.message_attributes and isinstance(self.message_attributes, str):
            self.message_attributes = json.loads(self.message_attributes)

        self.body = self._load_body()

    def _load_body(self):
        try:
            return json.loads(self.body)

        except JSONDecodeError:
            return self.body

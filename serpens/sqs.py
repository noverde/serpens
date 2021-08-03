from json.decoder import JSONDecodeError
import boto3
import logging
import json

from uuid import UUID
from typing import Union
from dataclasses import dataclass
from functools import wraps


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
        # TODO: validar se record existe

        for record_raw in event["Records"]:
            record = Record(
                message_id=record_raw.get("messageId", None),
                receipt_handle=record_raw.get("receiptHandle", None),
                body=record_raw.get("body", None),
                attributes=record_raw.get("attributes", None),
                message_attributes=record_raw.get("messageAttributes", None),
                md5_of_message_attributes=record_raw.get("md5OfMessageAttributes", None),
                md5_of_body=record_raw.get("md5OfBody", None),
                event_source=record_raw.get("eventSource", None),
                event_source_arn=record_raw.get("eventSourceARN", None),
                aws_region=record_raw.get("awsRegion", None),
            )
            func(record)

    return wrapper


@dataclass
class Record:
    body: Union[str, dict]
    message_id: UUID = None
    receipt_handle: str = None
    attributes: dict = None
    message_attributes: dict = None
    md5_of_message_attributes: str = None
    md5_of_body: str = None
    event_source: str = None
    event_source_arn: str = None
    aws_region: str = None

    def __post_init__(self):
        if self.attributes and isinstance(self.attributes, str):
            self.attributes = json.loads(self.attributes)

        if self.attributes and isinstance(self.message_attributes, str):
            self.message_attributes = json.loads(self.message_attributes)

        self.body = self._load_body()

    def _load_body(self):
        try:
            return json.loads(self.body)

        except JSONDecodeError:
            return self.body

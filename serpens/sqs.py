import json
import boto3
import logging

from typing import Union
from functools import wraps
from typing import Dict, Any
from datetime import datetime
from dataclasses import dataclass
from json.decoder import JSONDecodeError

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


@dataclass
class Record:
    data: Dict[Any, Any]

    @property
    def queue_name(self) -> str:
        arn_raw = self.data.get("eventSourceARN", "")

        if arn_raw:
            return arn_raw.split(":")[-1]

    @property
    def messageAttributes(self) -> Dict[Any, Any]:
        message_attributes = self.data.get("messageAttributes")

        if message_attributes and isinstance(message_attributes, str):
            return json.loads(message_attributes)
        return message_attributes

    @property
    def sent_datetime(self) -> datetime:
        return datetime.fromtimestamp(
            float(self.data["attributes"]["SentTimestamp"]) / 1000.0,
        )

    @property
    def body(self) -> Union[dict, str]:
        body_raw = self.data.get("body")

        try:
            return json.loads(body_raw)

        except JSONDecodeError:
            return body_raw

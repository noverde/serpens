import json
import logging
from datetime import datetime
from functools import wraps
from json.decoder import JSONDecodeError
import numbers
from typing import Any, Dict, Union
from uuid import uuid4

import boto3

from serpens.schema import SchemaEncoder
from serpens import initializers, elastic

initializers.setup()

logger = logging.getLogger(__name__)


def get_attributes(obj):
    if isinstance(obj, str):
        return {"StringValue": obj, "DataType": "String"}
    elif isinstance(obj, numbers.Number):
        return {"StringValue": obj, "DataType": "Number"}
    elif isinstance(obj, bytes):
        return {"BinaryValue": obj, "DataType": "Binary"}
    else:
        raise ValueError(f"Invalid data type for attribute {obj}")


def publish_message_batch(queue_url, messages, message_group_id=None):
    client = boto3.client("sqs")
    entries = []

    params = {"QueueUrl": queue_url}

    if queue_url.endswith(".fifo"):
        params["MessageGroupId"] = message_group_id
        params["MessageDeduplicationId"] = message_group_id

    for message in messages:
        message_attributes = {}

        body = message["body"] or {}
        if isinstance(body, dict):
            body = json.dumps(body, cls=SchemaEncoder)

        entry = {"Id": str(uuid4()), "MessageBody": body}

        for key, value in message.get("attributes", {}).items():
            message_attributes[key] = get_attributes(value)

        if message_attributes:
            entry["MessageAttributes"] = message_attributes

        entries.append(entry)

    params["Entries"] = entries

    return client.send_message_batch(**params)


def publish_message(queue_url, body, message_group_id=None):
    client = boto3.client("sqs")

    if isinstance(body, dict):
        body = json.dumps(body, cls=SchemaEncoder)

    params = {"QueueUrl": queue_url, "MessageBody": body}

    if queue_url.endswith(".fifo"):
        params["MessageGroupId"] = message_group_id
        params["MessageDeduplicationId"] = message_group_id

    return client.send_message(**params)


def handler(func):
    @wraps(func)
    @elastic.logger
    def wrapper(event: dict, context: dict):
        logger.debug(f"Received data: {event}")

        try:
            for data in event["Records"]:
                func(Record(data))
        except Exception as ex:
            logger.exception(ex)
            raise ex

    return wrapper


class Record:
    def __init__(self, data: Dict[Any, Any]):
        self.data = data
        self.queue_name = self._queue_name()
        self.message_attributes = data.get("messageAttributes")
        self.sent_datetime = self._sent_datetime()
        self.body = self._body()

    def _queue_name(self) -> str:
        arn_raw = self.data.get("eventSourceARN", "")
        return arn_raw.split(":")[-1]

    def _sent_datetime(self) -> datetime:
        return datetime.fromtimestamp(
            float(self.data["attributes"]["SentTimestamp"]) / 1000.0,
        )

    def _body(self) -> Union[dict, str]:
        body_raw = self.data.get("body")

        try:
            return json.loads(body_raw)

        except JSONDecodeError:
            return body_raw

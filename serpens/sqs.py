import json
import logging
from datetime import datetime
from functools import wraps
from json.decoder import JSONDecodeError
from typing import Any, Dict, Union
from uuid import uuid4

import boto3

from serpens.schema import SchemaEncoder
from serpens import initializers, elastic

initializers.setup()

logger = logging.getLogger(__name__)


def publish_message_batch(queue_url, messages, message_group_id=None):
    """
    Function that use boto3 to send batch messages (max messages allowed is up to 10).
    """
    client = boto3.client("sqs")
    entries = []
    attributes = {}

    for message in messages:
        body = message["body"]
        if isinstance(body, dict):
            body = json.dumps(body, cls=SchemaEncoder)

        params = {"QueueUrl": queue_url}

        if queue_url.endswith(".fifo"):
            params["MessageGroupId"] = message_group_id
            params["MessageDeduplicationId"] = message_group_id

        for attribute in message["attributes"]:
            for key, value in attribute.items():
                attributes[key] = {"StringValue": value["value"], "DataType": value["type"]}

        entry = {
            "Id": str(uuid4()),
            "MessageBody": body,
            "MessageAttributes": attributes,
        }

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

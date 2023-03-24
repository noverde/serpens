import json
import logging
from datetime import datetime
from functools import wraps
from json.decoder import JSONDecodeError
from typing import Any, Dict, Union

import boto3

from serpens.schema import SchemaEncoder
from serpens import initializers, elastic

initializers.setup()

logger = logging.getLogger(__name__)

SQS_MESSAGE_BATCH_SIZE = 10


def send_batch_message(queue_url, entries):
    client = boto3.client("sqs")
    response = client.send_message_batch(QueueUrl=queue_url, Entries=entries)
    if "Failed" in response:
        failed_ids = [msg["Id"] for msg in response["Failed"]]
        return failed_ids


def publish_message_batch(queue_url, messages, message_attributes={}, batch_size=10):
    entries = []
    failed_messages = []
    if batch_size >= SQS_MESSAGE_BATCH_SIZE:
        batch_size = SQS_MESSAGE_BATCH_SIZE

    for body in messages:
        if isinstance(body, dict):
            body = json.dumps(body, cls=SchemaEncoder)
        entry = {
            "Id": body.get("id"),
            "MessageBody": body,
            "MessageAttributes": message_attributes,
        }

        entries.append(entry)

        if len(entries) == batch_size:
            failed_list = send_batch_message(queue_url, entries)
            entries_failed = [entry for entry in entries if entry["id"] in failed_list]
            failed_messages.extend(entries_failed)
            entries = []

    if len(entries) > 0:
        failed_list = send_batch_message(queue_url, entries)
        entries_failed = [entry for entry in entries if entry["Id"] in failed_list]
        failed_messages.extend(entries_failed)

    return failed_messages


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

import json
import logging
import numbers
from datetime import datetime
from functools import wraps
from json.decoder import JSONDecodeError
import traceback
from typing import Any, Dict, Union
from uuid import uuid4
import os

import boto3

from serpens import elastic, initializers
from serpens.schema import SchemaEncoder
from serpens.sentry import FilteredEvent

initializers.setup()

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 10


def get_cloud_provider():
    return os.getenv("CLOUD_PROVIDER", "aws")


def build_message_attributes(attributes):
    message_attributes = {}

    for key, value in attributes.items():
        if isinstance(value, str):
            attributes = {"StringValue": value, "DataType": "String"}
        elif isinstance(value, numbers.Number):
            attributes = {"StringValue": value, "DataType": "Number"}
        elif isinstance(value, bytes):
            attributes = {"BinaryValue": value, "DataType": "Binary"}
        else:
            raise ValueError(f"Invalid data type for attribute {value}")
        message_attributes[key] = attributes
    return message_attributes


def publish_message_batch(queue_url, messages, order_key=None):
    message_group_id = order_key
    client = boto3.client("sqs")
    entries = []
    result = []

    params = {"QueueUrl": queue_url}

    if queue_url.endswith(".fifo"):
        params["MessageGroupId"] = message_group_id
        params["MessageDeduplicationId"] = message_group_id

    for message in messages:
        message_attributes = {}

        body = message["body"] or {}
        if not isinstance(body, str):
            body = json.dumps(body, cls=SchemaEncoder)

        entry = {"Id": str(uuid4()), "MessageBody": body}

        message_attributes = build_message_attributes(message.get("attributes", {}))

        if message_attributes:
            entry["MessageAttributes"] = message_attributes

        entries.append(entry)

        if len(entries) == MAX_BATCH_SIZE:
            params["Entries"] = entries
            sent_message = client.send_message_batch(**params)
            result.append(sent_message)
            entries = []

    if entries:
        params["Entries"] = entries
        sent_message = client.send_message_batch(**params)
        result.append(sent_message)

    return result


def publish_message(queue_url, body, message_group_id=None, attributes=None):
    client = boto3.client("sqs")

    if not isinstance(body, str):
        body = json.dumps(body, cls=SchemaEncoder)

    params = {"QueueUrl": queue_url, "MessageBody": body}

    message_attributes = None
    if attributes is not None:
        message_attributes = build_message_attributes(attributes)

    if message_attributes:
        params["MessageAttributes"] = message_attributes

    if queue_url.endswith(".fifo"):
        params["MessageGroupId"] = message_group_id
        params["MessageDeduplicationId"] = message_group_id

    return client.send_message(**params)


def handler(func):
    """
    Decorator to handle batch processing of events.
    - Logs incoming data.
    - Processes each record in the event.
    - Handles exceptions and returns a list of failed items.
    """

    @wraps(func)
    def wrapper(event: dict, _: dict):
        logger.debug(f"Received data: {event}")
        cloud_provider = get_cloud_provider()
        events_failed = []

        for data in event["Records"]:
            try:
                result = func(Record(data))
            except Exception as e:
                logger.error(f"Error processing record {data}: {e}\n{traceback.format_exc()}")

                if isinstance(e, FilteredEvent):
                    elastic.set_transaction_result("failure", override=False)
                    elastic.capture_exception(e)

                    if cloud_provider == "aws":
                        events_failed.append({"itemIdentifier": data.get("messageId")})
                    else:
                        raise FilteredEvent(
                            f"Unsupported cloud provider or invalid event data: {event}"
                        )
                else:
                    # Relevanta a exceção original para não mascarar
                    raise
            else:
                if cloud_provider == "aws":
                    if isinstance(result, dict) and "messageId" in result:
                        events_failed.append({"itemIdentifier": result["messageId"]})

        if events_failed:
            result = {"batchItemFailures": events_failed}
            logger.debug(f"Result data: {result}")
            return result

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

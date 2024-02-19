import json
from typing import Any, Dict, List, Optional

from google.cloud import pubsub_v1

from serpens.schema import SchemaEncoder

MAX_BATCH_SIZE = 10


def publish_message(
    topic: str,
    data: Any,
    ordering_key: str = "",
    attributes: Optional[Dict[str, Any]] = None,
) -> str:
    publisher_options = pubsub_v1.types.PublisherOptions(enable_message_ordering=bool(ordering_key))
    publisher = pubsub_v1.PublisherClient(publisher_options=publisher_options)

    if not isinstance(data, str):
        data = json.dumps(data, cls=SchemaEncoder)

    message = data.encode("utf-8")

    if attributes is None:
        attributes = {}

    if ":" in topic:
        topic, endpoint = topic.split(":")
        attributes["endpoint"] = endpoint

    if ordering_key is None:
        ordering_key = ""

    future = publisher.publish(topic, data=message, ordering_key=ordering_key, **attributes)

    return future.result()


def publish_message_batch(topic: str, messages: List[Dict], ordering_key: str = "") -> List[str]:
    publisher_options = pubsub_v1.types.PublisherOptions(enable_message_ordering=bool(ordering_key))
    batch_settings = pubsub_v1.types.BatchSettings(max_messages=MAX_BATCH_SIZE)
    publisher = pubsub_v1.PublisherClient(
        batch_settings=batch_settings, publisher_options=publisher_options
    )

    futures = []
    endpoint = None

    if ":" in topic:
        topic, endpoint = topic.split(":")

    if ordering_key is None:
        ordering_key = ""

    for message in messages:
        if not isinstance(message["body"], str):
            message["body"] = json.dumps(message["body"], cls=SchemaEncoder)

        body = message["body"].encode("utf-8")

        if "attributes" not in message:
            message["attributes"] = {}

        if endpoint is not None:
            message["attributes"]["endpoint"] = endpoint

        future = publisher.publish(
            topic, data=body, ordering_key=ordering_key, **message["attributes"]
        )

        futures.append(future)

    return [f.result() for f in futures]

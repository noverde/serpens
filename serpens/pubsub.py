import json
from typing import Any, Dict, List, Optional

from google.cloud import pubsub_v1

from serpens.schema import SchemaEncoder


def publish_message(
    topic: str, data: Any, ordering_key: str = "", attributes: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    publisher = pubsub_v1.PublisherClient()

    if not isinstance(data, str):
        data = json.dumps(data, cls=SchemaEncoder)

    message = data.encode("utf-8")

    if attributes is None:
        attributes = {}

    if ":" in topic:
        topic, endpoint = topic.split(":")
        attributes["endpoint"] = endpoint

    future = publisher.publish(topic, data=message, ordering_key=ordering_key, **attributes)

    return future.result()


def publish_message_batch(topic: str, messages: List[Dict], ordering_key: str = "") -> List[str]:
    publisher = pubsub_v1.PublisherClient()
    results = []
    endpoint = None

    if ":" in topic:
        topic, endpoint = topic.split(":")

    for message in messages:
        if not isinstance(message["body"], str):
            message["body"] = json.dumps(message["body"], cls=SchemaEncoder)

        body = message["body"].encode("utf-8")

        if message.get("attributes") is None:
            message["attributes"] = {}

        if endpoint is not None:
            message["attributes"]["endpoint"] = endpoint

        future = publisher.publish(
            topic, data=body, ordering_key=ordering_key, **message["attributes"]
        )

        results.append(future.result())

    return results

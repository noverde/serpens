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


def publish_message_batch(topic: str, datas: List[Dict], ordering_key: str = "") -> List[str]:
    publisher = pubsub_v1.PublisherClient()
    future = []

    if ":" in topic:
        topic, endpoint = topic.split(":")

    for data in datas:
        if not isinstance(data["body"], str):
            data["body"] = json.dumps(data["body"], cls=SchemaEncoder)

        message = data["body"].encode("utf-8")

        if data["attributes"] is None:
            data["attributes"] = {}

        if endpoint is not None:
            data["attributes"]["endpoint"] = endpoint

        future.append(
            publisher.publish(
                topic, data=message, ordering_key=ordering_key, **data["attributes"]
            ).result()
        )

    return future

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


def publish_message_batch(topic: str, data: List[Dict], ordering_key: str = "") -> List[str]:
    publisher = pubsub_v1.PublisherClient()
    results = []

    if ":" in topic:
        topic, endpoint = topic.split(":")

    for _data in data:
        if not isinstance(_data["body"], str):
            _data["body"] = json.dumps(_data["body"], cls=SchemaEncoder)

        message = _data["body"].encode("utf-8")

        if _data["attributes"] is None:
            _data["attributes"] = {}

        if endpoint is not None:
            _data["attributes"]["endpoint"] = endpoint

        future = publisher.publish(
            topic, _data=message, ordering_key=ordering_key, **_data["attributes"]
        )

        results.append(future.result())

    return results

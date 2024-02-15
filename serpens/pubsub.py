import json
from typing import Any, Dict, Optional
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

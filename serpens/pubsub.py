import json
from typing import Dict, Optional
from google.cloud import pubsub_v1

from serpens.schema import SchemaEncoder


def publish_message(
    topic, data, ordering_key: str = "", attributes: Optional[Dict[str, any]] = None
):
    publisher = pubsub_v1.PublisherClient()

    if not isinstance(data, str):
        data = json.dumps(data, cls=SchemaEncoder)

    if attributes is None:
        attributes = {}

    message = data.encode("utf-8")

    future = publisher.publish(topic, data=message, ordering_key=ordering_key, **attributes)

    return future.result()

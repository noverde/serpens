import asyncio
import json
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from google.cloud import pubsub_v1

from serpens.schema import SchemaEncoder

try:
    from elasticapm import capture_span
except ImportError:  # pragma: no cover
    capture_span = None


@contextmanager
def _messaging_span(topic: str):
    if capture_span is None:
        yield None
        return
    with capture_span(topic, span_type="messaging") as span:
        yield span


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


class AsyncPublisher:
    """Async wrapper over `pubsub_v1.PublisherClient` for FastAPI / asyncio apps.

    `topic` is a full topic id (`projects/PROJECT/topics/NAME`) — the same
    value our Terraform exposes as an env var. Emits an `elasticapm`
    messaging span per publish when APM is available.
    """

    def __init__(self, ordering_key: str = ""):
        publisher_options = pubsub_v1.types.PublisherOptions(
            enable_message_ordering=bool(ordering_key)
        )
        self._client = pubsub_v1.PublisherClient(publisher_options=publisher_options)
        self._ordering_key = ordering_key

    async def publish(
        self,
        topic: str,
        data: Any,
        ordering_key: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not isinstance(data, str):
            data = json.dumps(data, cls=SchemaEncoder)
        message = data.encode("utf-8")

        if attributes is None:
            attributes = {}

        if ":" in topic:
            topic, endpoint = topic.split(":")
            attributes["endpoint"] = endpoint

        key = self._ordering_key if ordering_key is None else ordering_key

        with _messaging_span(topic) as span:
            future = self._client.publish(topic, data=message, ordering_key=key, **attributes)
            message_id = await asyncio.wrap_future(future)
            if span is not None and hasattr(span, "label"):
                span.label(queue_name=topic)
            return message_id

    def close(self) -> None:
        self._client.transport.close()

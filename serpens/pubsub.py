import logging

from google.cloud import pubsub_v1

logger = logging.getLogger(__name__)


def publish_message(message_destination, body, attributes={}):
    logger.debug(f"Received message: {body}")
    logger.debug(f"Received destination: {message_destination}")
    logger.debug(f"Received attributes: {attributes}")

    publisher = pubsub_v1.PublisherClient()
    message = body.encode("utf-8")

    future = publisher.publish(message_destination, data=message, **attributes)
    result = future.result()

    logger.debug(f"Received result: {result}")
    return result

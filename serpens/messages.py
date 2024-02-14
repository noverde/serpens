import logging
import os
from enum import Enum
import sqs

logger = logging.getLogger(__name__)

MESSAGE_PROVIDER = os.getenv("MESSAGE_PROVIDER")


class MessageProvider(Enum):
    SQS = "sqs"


def send_message(message_url, message_body, message_group_id=None, message_attributes={}):
    logger.debug(f"Received message: {message_body}")
    logger.debug(f"Received url: {message_url}")
    logger.debug(f"Received attributes: {message_attributes}")

    if MESSAGE_PROVIDER == MessageProvider.SQS:
        sqs.publish_message(message_url, message_body, message_group_id, message_attributes)
    else:
        raise ValueError("Unsupported topic type or not configured")

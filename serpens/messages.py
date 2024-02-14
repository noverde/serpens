import logging
import os
from enum import Enum
import sqs

logger = logging.getLogger(__name__)

MESSAGE_PROVIDER = os.getenv("MESSAGE_PROVIDER")


class MessageProvider(Enum):
    SQS = "sqs"


def publish_message(
    message_destination, message_body, message_group_id=None, message_attributes={}
):
    logger.debug(f"Provider: {MESSAGE_PROVIDER}")

    if MESSAGE_PROVIDER == MessageProvider.SQS.value:
        sqs.publish_message(message_destination, message_body, message_group_id, message_attributes)
    else:
        raise ValueError("Unsupported message provider type or not configured")

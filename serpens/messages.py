import importlib
import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MessageProvider(Enum):
    SQS = "sqs"


class MessageClient:
    _instance = None

    def __init__(self, provider: Optional[MessageProvider] = None):
        self._provider = provider or MessageProvider(os.getenv("MESSAGE_PROVIDER"))
        logger.debug(f"Provider: {self._provider.value}")
        module = importlib.import_module(f"serpens.{self._provider.value}")
        self._publish = module.publish_message

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MessageClient, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def publish(
        cls,
        destination: str,
        body: Any,
        order_key: Optional[str] = None,
        attributes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        return cls()._publish(destination, body, order_key, attributes)

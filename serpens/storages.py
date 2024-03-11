import importlib
import logging
import os
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StorageProvider(Enum):
    S3 = "s3"
    CLOUD_STORAGE = "cloud_storage"


class StorageClient:
    _instance = None

    def __init__(self, provider: Optional[StorageProvider] = None):
        self._provider = provider or StorageProvider(os.getenv("STORAGE_PROVIDER"))
        logger.debug(f"Provider: {self._provider.value}")
        module = importlib.import_module(f"serpens.{self._provider.value}")
        self._get_object = module.get_object

    def get(
        self,
        bucket: str,
        key: str,
    ) -> Dict[str, Any]:
        object = self._get_object(bucket, key)

        return object

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

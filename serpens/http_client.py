"""Singleton `httpx.AsyncClient` for FastAPI / async apps."""

import os
from typing import Optional

from httpx import AsyncClient

_client: Optional[AsyncClient] = None


async def init_client(timeout: Optional[float] = None, **kwargs) -> AsyncClient:
    global _client
    if _client is not None:
        return _client
    if timeout is None:
        timeout = float(os.getenv("HTTP_CLIENT_TIMEOUT", "30"))
    _client = AsyncClient(timeout=timeout, **kwargs)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_client() -> AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client is not initialized. Did you call init_client()?")
    return _client

"""Asyncio token-bucket limiter for outbound calls plus an `auth_lock` to
serialize token refresh across concurrent callers.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, rate: int, per_seconds: float):
        if rate <= 0:
            raise ValueError("rate must be > 0")
        if per_seconds <= 0:
            raise ValueError("per_seconds must be > 0")
        self.rate = rate
        self.per_seconds = per_seconds
        self.semaphore = asyncio.Semaphore(rate)
        self.auth_lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def _replenish(self) -> None:
        sleep_time = self.per_seconds / self.rate
        while True:
            await asyncio.sleep(sleep_time)
            if self.semaphore._value < self.rate:
                self.semaphore.release()

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._replenish())
            logger.info("RateLimiter started: %d per %.2fs", self.rate, self.per_seconds)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("RateLimiter stopped")

    async def acquire(self) -> None:
        await self.semaphore.acquire()

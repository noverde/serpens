import asyncio
import time
import unittest

from rate_limit import RateLimiter


class RateLimiterTests(unittest.IsolatedAsyncioTestCase):
    def test_rejects_non_positive_args(self):
        with self.assertRaises(ValueError):
            RateLimiter(rate=0, per_seconds=1.0)
        with self.assertRaises(ValueError):
            RateLimiter(rate=1, per_seconds=0)

    async def test_acquire_paces_calls_when_bucket_drained(self):
        limiter = RateLimiter(rate=2, per_seconds=0.2)
        limiter.start()
        try:
            # Drain the bucket.
            await limiter.acquire()
            await limiter.acquire()

            start = time.monotonic()
            await limiter.acquire()
            elapsed = time.monotonic() - start
        finally:
            await limiter.stop()

        # Replenish interval is 0.2 / 2 = 0.1s; allow generous slack.
        self.assertGreater(elapsed, 0.05)

    async def test_stop_is_idempotent(self):
        limiter = RateLimiter(rate=1, per_seconds=1.0)
        limiter.start()
        await limiter.stop()
        await limiter.stop()  # no-op, must not raise

    async def test_auth_lock_serializes_concurrent_callers(self):
        limiter = RateLimiter(rate=10, per_seconds=1.0)
        observed = []

        async def task(i):
            async with limiter.auth_lock:
                observed.append(("enter", i))
                await asyncio.sleep(0.01)
                observed.append(("leave", i))

        await asyncio.gather(*(task(i) for i in range(3)))

        # Strict interleaving: every enter is followed by its matching leave before the next enter.
        for i in range(0, len(observed), 2):
            self.assertEqual(observed[i][0], "enter")
            self.assertEqual(observed[i + 1][0], "leave")
            self.assertEqual(observed[i][1], observed[i + 1][1])

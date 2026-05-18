import json
import unittest
from unittest.mock import AsyncMock, patch

import cache_async


class _AsyncRedisStub:
    def __init__(self):
        self.store = {}
        self.get = AsyncMock(side_effect=self._get)
        self.set = AsyncMock(side_effect=self._set)
        self.delete = AsyncMock(side_effect=self._delete)
        self.aclose = AsyncMock()

    async def _get(self, key):
        return self.store.get(key)

    async def _set(self, key, value, ex=None):
        self.store[key] = value

    async def _delete(self, key):
        self.store.pop(key, None)


class CacheAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.stub = _AsyncRedisStub()
        self._patcher = patch.object(cache_async.Redis, "from_url", return_value=self.stub)
        self._patcher.start()
        await cache_async.init(url="redis://test")

    async def asyncTearDown(self):
        await cache_async.close()
        self._patcher.stop()

    async def test_init_is_idempotent(self):
        again = await cache_async.init(url="redis://test")
        self.assertIs(again, self.stub)

    async def test_set_then_get_round_trips_through_json(self):
        await cache_async.set_("user:1", {"name": "Ana"}, ttl=10)
        self.assertEqual(self.stub.store[f"{cache_async.PREFIX}:user:1"], '{"name": "Ana"}')
        self.assertEqual(await cache_async.get("user:1"), {"name": "Ana"})

    async def test_get_returns_none_on_miss(self):
        self.assertIsNone(await cache_async.get("missing"))

    async def test_delete_removes_key(self):
        await cache_async.set_("x", 1)
        await cache_async.delete("x")
        self.assertIsNone(await cache_async.get("x"))

    async def test_cached_get_or_set_caches_on_miss(self):
        calls = []

        async def producer(arg):
            calls.append(arg)
            return {"value": arg * 2}

        a = await cache_async.cached_get_or_set("k", 60, producer, 21)
        b = await cache_async.cached_get_or_set("k", 60, producer, 21)
        self.assertEqual(a, {"value": 42})
        self.assertEqual(b, {"value": 42})
        self.assertEqual(calls, [21])  # producer ran exactly once

    async def test_cached_decorator_memoizes_per_args(self):
        calls = []

        @cache_async.cached("memo", ttl=60)
        async def f(x, y):
            calls.append((x, y))
            return x + y

        self.assertEqual(await f(1, 2), 3)
        self.assertEqual(await f(1, 2), 3)
        self.assertEqual(await f(2, 2), 4)
        self.assertEqual(calls, [(1, 2), (2, 2)])
        # Stored values are JSON-encoded.
        self.assertIn(f"{cache_async.PREFIX}:memo:1:2", self.stub.store)
        self.assertEqual(json.loads(self.stub.store[f"{cache_async.PREFIX}:memo:1:2"]), 3)

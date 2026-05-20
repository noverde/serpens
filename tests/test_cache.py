import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from redis.exceptions import ConnectionError as RedisConnectionError

import cache
from tests.fixtures.fixtures import ClsCached


def _fake_pool() -> MagicMock:
    """MagicMock that satisfies ``redis.asyncio.Redis.__init__``."""
    pool = MagicMock()
    pool.connection_kwargs = {}
    return pool


class TestSCache(unittest.TestCase):
    counter = 0

    @cache.cached("test_cache", 900)
    def get_cached_counter(self):
        self.counter += 1
        return self.counter

    def test_cache(self):
        strike1 = self.get_cached_counter()
        self.assertEqual(strike1, 1)

        strike2 = self.get_cached_counter()
        self.assertEqual(strike2, 1)

    def test_clear_cache(self):
        strike1 = self.get_cached_counter()
        self.assertEqual(strike1, 1)

        cache.clear_cache("test_cache")

        strike2 = self.get_cached_counter()
        self.assertEqual(strike2, 2)

    def test_cache_classmethod(self):
        strike1 = ClsCached.proc_cls()
        self.assertEqual(strike1, 1)

        strike2 = ClsCached.proc_cls()
        self.assertEqual(strike2, 1)

        cache.clear_cache("test_cache_cls")

        strike3 = ClsCached.proc_cls()
        self.assertEqual(strike3, 2)

    def test_cache_method(self):
        obj = ClsCached()

        strike1 = obj.proc_self()
        self.assertEqual(strike1, 1)

        strike2 = obj.proc_self()
        self.assertEqual(strike2, 1)

        cache.clear_cache("test_cache_self")

        strike3 = obj.proc_self()
        self.assertEqual(strike3, 2)


class AsyncInmemCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        cache.clear_acache()

    async def test_acached_returns_stored_value_within_ttl(self):
        calls = []

        @cache.acached("memo", ttl_seconds=60)
        async def f(self_, x):
            calls.append(x)
            return x * 2

        self.assertEqual(await f(None, 5), 10)
        self.assertEqual(await f(None, 5), 10)
        self.assertEqual(calls, [5])

    async def test_acached_recomputes_after_ttl_expires(self):
        calls = []

        @cache.acached("memo", ttl_seconds=10)
        async def f(self_, x):
            calls.append(x)
            return x

        with patch("cache.time.monotonic", return_value=1000.0):
            await f(None, "a")
        with patch("cache.time.monotonic", return_value=1005.0):
            await f(None, "a")  # within TTL
        with patch("cache.time.monotonic", return_value=1011.0):
            await f(None, "a")  # past TTL

        self.assertEqual(calls, ["a", "a"])

    async def test_acached_ignores_first_positional_arg_in_key(self):
        @cache.acached("memo", ttl_seconds=60)
        async def f(owner, x):
            return f"{owner}:{x}"

        first = await f("owner-A", 1)
        second = await f("owner-B", 1)
        self.assertEqual(first, second)
        self.assertEqual(first, "owner-A:1")

    async def test_acached_distinguishes_args_and_sorted_kwargs(self):
        calls = []

        @cache.acached("memo", ttl_seconds=60)
        async def f(self_, x, *, flag):
            calls.append((x, flag))
            return (x, flag)

        await f(None, 1, flag=True)
        await f(None, 1, flag=False)
        await f(None, 1, flag=True)  # hit
        self.assertEqual(calls, [(1, True), (1, False)])

    async def test_clear_acache_by_name_drops_only_that_bucket(self):
        @cache.acached("alpha", ttl_seconds=60)
        async def a(self_):
            return "A"

        @cache.acached("beta", ttl_seconds=60)
        async def b(self_):
            return "B"

        await a(None)
        await b(None)
        self.assertIn("alpha", cache._acache)
        self.assertIn("beta", cache._acache)

        cache.clear_acache("alpha")
        self.assertNotIn("alpha", cache._acache)
        self.assertIn("beta", cache._acache)

    async def test_clear_acache_no_arg_drops_everything(self):
        @cache.acached("alpha", ttl_seconds=60)
        async def a(self_):
            return "A"

        await a(None)
        cache.clear_acache()
        self.assertEqual(cache._acache, {})


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


class RedisCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.stub = _AsyncRedisStub()
        self._patcher = patch.object(cache.Redis, "from_url", return_value=self.stub)
        self._patcher.start()
        await cache.redis_init(url="redis://test")

    async def asyncTearDown(self):
        await cache.redis_close()
        self._patcher.stop()

    async def test_redis_init_is_idempotent(self):
        again = await cache.redis_init(url="redis://test")
        self.assertIs(again, self.stub)

    async def test_redis_set_then_get_round_trips_through_json(self):
        await cache.redis_set("user:1", {"name": "Ana"}, ttl=10)
        self.assertEqual(self.stub.store[f"{cache.REDIS_PREFIX}:user:1"], '{"name": "Ana"}')
        self.assertEqual(await cache.redis_get("user:1"), {"name": "Ana"})

    async def test_redis_get_returns_none_on_miss(self):
        self.assertIsNone(await cache.redis_get("missing"))

    async def test_redis_delete_removes_key(self):
        await cache.redis_set("x", 1)
        await cache.redis_delete("x")
        self.assertIsNone(await cache.redis_get("x"))

    async def test_redis_cached_get_or_set_caches_on_miss(self):
        calls = []

        async def producer(arg):
            calls.append(arg)
            return {"value": arg * 2}

        a = await cache.redis_cached_get_or_set("k", 60, producer, 21)
        b = await cache.redis_cached_get_or_set("k", 60, producer, 21)
        self.assertEqual(a, {"value": 42})
        self.assertEqual(b, {"value": 42})
        self.assertEqual(calls, [21])

    async def test_redis_cached_decorator_memoizes_per_args(self):
        calls = []

        @cache.redis_cached("memo", ttl=60)
        async def f(x, y):
            calls.append((x, y))
            return x + y

        self.assertEqual(await f(1, 2), 3)
        self.assertEqual(await f(1, 2), 3)
        self.assertEqual(await f(2, 2), 4)
        self.assertEqual(calls, [(1, 2), (2, 2)])
        self.assertIn(f"{cache.REDIS_PREFIX}:memo:1:2", self.stub.store)
        self.assertEqual(json.loads(self.stub.store[f"{cache.REDIS_PREFIX}:memo:1:2"]), 3)


class RedisCacheFaultToleranceTests(unittest.IsolatedAsyncioTestCase):
    """A Redis outage must not break callers."""

    async def asyncSetUp(self):
        self.stub = _AsyncRedisStub()
        self.stub.get.side_effect = RedisConnectionError("host unreachable")
        self.stub.set.side_effect = RedisConnectionError("host unreachable")
        self.stub.delete.side_effect = RedisConnectionError("host unreachable")
        self._patcher = patch.object(cache.Redis, "from_url", return_value=self.stub)
        self._patcher.start()
        await cache.redis_init(url="redis://test")

    async def asyncTearDown(self):
        await cache.redis_close()
        self._patcher.stop()

    async def test_redis_get_returns_none_when_redis_unreachable(self):
        self.assertIsNone(await cache.redis_get("anything"))

    async def test_redis_set_swallows_redis_error(self):
        await cache.redis_set("k", {"v": 1})

    async def test_redis_delete_swallows_redis_error(self):
        await cache.redis_delete("k")

    async def test_redis_cached_get_or_set_falls_through_to_func_on_failure(self):
        calls = []

        async def producer():
            calls.append(1)
            return {"value": 42}

        result = await cache.redis_cached_get_or_set("k", 60, producer)
        self.assertEqual(result, {"value": 42})
        self.assertEqual(calls, [1])

    async def test_redis_cached_decorator_keeps_serving_during_outage(self):
        calls = []

        @cache.redis_cached("memo", ttl=60)
        async def f(x):
            calls.append(x)
            return x * 2

        self.assertEqual(await f(5), 10)
        self.assertEqual(await f(5), 10)
        self.assertEqual(calls, [5, 5])

    async def test_redis_get_propagates_runtime_error_when_uninitialized(self):
        await cache.redis_close()
        with self.assertRaises(RuntimeError):
            await cache.redis_get("anything")


class RedisPoolTests(unittest.IsolatedAsyncioTestCase):
    async def test_redis_pool_returns_callable(self):
        pool = cache.redis_pool("redis://test")
        self.assertTrue(callable(pool))

    async def test_redis_pool_yields_safe_redis(self):
        with patch.object(cache, "ConnectionPool") as pool_cls:
            pool_cls.from_url.return_value = _fake_pool()
            pool = cache.redis_pool("redis://test")
            gen = pool()
            with patch.object(cache._SafeRedis, "aclose", new=AsyncMock()):
                client = await gen.__anext__()
                self.assertIsInstance(client, cache._SafeRedis)
                with self.assertRaises(StopAsyncIteration):
                    await gen.__anext__()

    async def test_safe_redis_get_returns_none_on_redis_error(self):
        client = cache._SafeRedis(connection_pool=_fake_pool())
        with patch.object(
            cache.Redis, "get", new=AsyncMock(side_effect=RedisConnectionError("down"))
        ):
            self.assertIsNone(await client.get("k"))

    async def test_safe_redis_set_swallows_redis_error(self):
        client = cache._SafeRedis(connection_pool=_fake_pool())
        with patch.object(
            cache.Redis, "set", new=AsyncMock(side_effect=RedisConnectionError("down"))
        ):
            self.assertIsNone(await client.set("k", "v"))

    async def test_safe_redis_delete_returns_zero_on_redis_error(self):
        client = cache._SafeRedis(connection_pool=_fake_pool())
        with patch.object(
            cache.Redis, "delete", new=AsyncMock(side_effect=RedisConnectionError("down"))
        ):
            self.assertEqual(await client.delete("k"), 0)

    async def test_safe_redis_passes_through_on_success(self):
        client = cache._SafeRedis(connection_pool=_fake_pool())
        with patch.object(cache.Redis, "get", new=AsyncMock(return_value="value")):
            self.assertEqual(await client.get("k"), "value")

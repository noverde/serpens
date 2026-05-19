import unittest
from unittest.mock import patch

import cache_inmem


class CacheInmemTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        cache_inmem.clear_cache()

    async def test_cached_returns_stored_value_within_ttl(self):
        calls = []

        @cache_inmem.cached("memo", ttl_seconds=60)
        async def f(self_, x):
            calls.append(x)
            return x * 2

        self.assertEqual(await f(None, 5), 10)
        self.assertEqual(await f(None, 5), 10)
        self.assertEqual(calls, [5])

    async def test_cached_recomputes_after_ttl_expires(self):
        calls = []

        @cache_inmem.cached("memo", ttl_seconds=10)
        async def f(self_, x):
            calls.append(x)
            return x

        with patch("cache_inmem.time.monotonic", return_value=1000.0):
            await f(None, "a")
        with patch("cache_inmem.time.monotonic", return_value=1005.0):
            await f(None, "a")  # within TTL
        with patch("cache_inmem.time.monotonic", return_value=1011.0):
            await f(None, "a")  # past TTL

        self.assertEqual(calls, ["a", "a"])

    async def test_cached_ignores_first_positional_arg_in_key(self):
        @cache_inmem.cached("memo", ttl_seconds=60)
        async def f(owner, x):
            return f"{owner}:{x}"

        # Different owners, same business args ⇒ same cache hit.
        first = await f("owner-A", 1)
        second = await f("owner-B", 1)
        self.assertEqual(first, second)
        self.assertEqual(first, "owner-A:1")

    async def test_cached_distinguishes_args_and_sorted_kwargs(self):
        calls = []

        @cache_inmem.cached("memo", ttl_seconds=60)
        async def f(self_, x, *, flag):
            calls.append((x, flag))
            return (x, flag)

        await f(None, 1, flag=True)
        await f(None, 1, flag=False)
        await f(None, 1, flag=True)  # hit
        self.assertEqual(calls, [(1, True), (1, False)])

    async def test_clear_cache_by_name_drops_only_that_bucket(self):
        @cache_inmem.cached("alpha", ttl_seconds=60)
        async def a(self_):
            return "A"

        @cache_inmem.cached("beta", ttl_seconds=60)
        async def b(self_):
            return "B"

        await a(None)
        await b(None)
        self.assertIn("alpha", cache_inmem._cache)
        self.assertIn("beta", cache_inmem._cache)

        cache_inmem.clear_cache("alpha")
        self.assertNotIn("alpha", cache_inmem._cache)
        self.assertIn("beta", cache_inmem._cache)

    async def test_clear_cache_no_arg_drops_everything(self):
        @cache_inmem.cached("alpha", ttl_seconds=60)
        async def a(self_):
            return "A"

        await a(None)
        cache_inmem.clear_cache()
        self.assertEqual(cache_inmem._cache, {})


if __name__ == "__main__":
    unittest.main()

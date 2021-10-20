import cache
import unittest

from tests.fixtures.fixtures import ClsCached


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

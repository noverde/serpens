import unittest

import cache


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

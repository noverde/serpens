import unittest

import settings


class TestSettings(unittest.TestCase):
    def test_settings(self):
        self.assertEqual(settings.APPNAME, "serpens")

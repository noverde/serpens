import unittest

import initializers


class TestInitializers(unittest.TestCase):
    def test_init_logger(self):
        initializers.init_logger()

    def test_init_sentry(self):
        initializers.init_logger()

    def test_setup(self):
        initializers.setup()

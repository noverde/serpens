import os
import unittest

import initializers


class TestInitializers(unittest.TestCase):
    def unsetvar(self, envvar: str):
        if os.getenv(envvar):
            del os.environ[envvar]

    def test_init_logger_disabled(self):
        self.unsetvar("LOG_LEVEL")
        initializers.init_logger()

    def test_init_sentry_enabled(self):
        os.environ["SENTRY_DSN"] = ""
        initializers.init_logger()

    def test_init_sentry_disabled(self):
        self.unsetvar("SENTRY_DSN")
        initializers.init_logger()

    def test_setup(self):
        initializers.setup()

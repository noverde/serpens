import os
import unittest

from serpens import initializers, log, sentry


class TestInitializers(unittest.TestCase):
    def unsetvar(self, envvar: str):
        if os.getenv(envvar):
            del os.environ[envvar]

    def test_init_logger_disabled(self):
        self.unsetvar("LOG_LEVEL")
        log.setup()

    def test_init_sentry_enabled(self):
        os.environ["SENTRY_DSN"] = ""
        sentry.setup()

    def test_init_sentry_disabled(self):
        self.unsetvar("SENTRY_DSN")
        sentry.setup()

    def test_setup(self):
        initializers.setup()

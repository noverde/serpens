import unittest
from unittest.mock import patch

from serpens.elastic import logger, set_transaction_result, setup


class TestElastic(unittest.TestCase):
    def setUp(self):
        def to_be_decorated(event, context, **kwargs):
            pass

        self.function = to_be_decorated
        self.elastic_patcher = patch("serpens.elastic.elasticapm")
        self.mock_elastic = self.elastic_patcher.start()
        self.m_capture_serverless = self.mock_elastic.capture_serverless

        self.os_patcher = patch("serpens.elastic.os")
        self.os_mock = self.os_patcher.start()
        self.os_mock.environ = {}

    def tearDown(self):
        self.elastic_patcher.stop()
        self.os_patcher.stop()

    def test_logger_decorator_not_called(self):
        event, context = {}, {}

        logger(self.function)(event, context)
        self.m_capture_serverless.assert_not_called()

    def test_logger_decorator_called(self):
        self.os_mock.environ["ELASTIC_APM_SECRET_TOKEN"] = "123456"
        event, context = {}, {"key": "value"}

        logger(self.function)(event, context)
        self.m_capture_serverless.assert_called_once()
        self.m_capture_serverless.assert_called_with(self.function)

    def test_set_transaction_result_with_elastic(self):
        self.os_mock.environ["ELASTIC_APM_SECRET_TOKEN"] = "123456"
        set_transaction_result("Failure", False)
        self.mock_elastic.set_transaction_result.assert_called_once_with("Failure", override=False)

    def test_set_transaction_result_without_elastic(self):
        set_transaction_result("Failure", False)
        self.mock_elastic.set_transaction_result.assert_not_called()

    def test_setup(self):
        self.os_mock.environ["ELASTIC_APM_SECRET_TOKEN"] = "123456"
        setup()

        apm_processors = self.os_mock.environ.get("ELASTIC_APM_PROCESSORS")

        self.assertIsNotNone(apm_processors)
        self.assertTrue("serpens.elastic_sanitize.sanitize" in apm_processors)

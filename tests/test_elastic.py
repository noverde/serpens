from serpens import elastic
from serpens.elastic import logger, set_transaction_result
from unittest.mock import patch
import unittest


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

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    def test_logger_decorator_called(self):
        event, context = {}, {"key": "value"}

        logger(self.function)(event, context)
        self.m_capture_serverless.assert_called_once()
        self.m_capture_serverless.assert_called_with(self.function)

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    def test_set_transaction_result_with_elastic(self):
        set_transaction_result("Failure", False)
        self.mock_elastic.set_transaction_result.assert_called_once_with("Failure", override=False)

    def test_set_transaction_result_without_elastic(self):
        set_transaction_result("Failure", False)
        self.mock_elastic.set_transaction_result.assert_not_called()

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    def test_setup(self):
        elastic.setup()

        apm_processors = self.os_mock.environ.get("ELASTIC_APM_PROCESSORS")

        self.assertIsNotNone(apm_processors)
        self.assertTrue("serpens.elastic_sanitize.sanitize_http_request_body" in apm_processors)
        self.assertTrue("serpens.elastic_sanitize.sanitize_http_response_body" in apm_processors)

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    @patch("serpens.elastic.ELASTIC_APM_CAPTURE_RESPONSE_BODY", True)
    def test_capture_response(self):
        body = {"name": "Test", "password": 12345}

        elastic.capture_response(body)
        self.mock_elastic.set_custom_context.assert_called_once_with({"response_body": body})

    def test_capture_response_disabled(self):
        body = {"name": "Test", "password": 12345}
        elastic.capture_response(body)
        self.mock_elastic.set_custom_context.assert_not_called()

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    def test_capture_response_disabled_with_apm_enabled(self):
        body = {"name": "Test", "password": 12345}
        elastic.capture_response(body)
        self.mock_elastic.set_custom_context.assert_not_called()

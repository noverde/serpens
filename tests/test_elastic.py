from serpens import elastic
from serpens.elastic import logger, set_transaction_result
from unittest.mock import patch
import unittest


class TestElastic(unittest.TestCase):
    def _getenv(self, key, default=None):
        return self.os_mock.environ.get(key, default)

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
        self.os_mock.getenv = self._getenv

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
    @patch("serpens.elastic.ELASTIC_APM_CAPTURE_BODY", True)
    def test_setup(self):
        elastic.setup()

        processors = self.os_mock.environ.get("ELASTIC_APM_PROCESSORS")

        processors_expected = (
            "serpens.elastic_sanitize.sanitize_http_request_body,"
            "serpens.elastic_sanitize.sanitize_http_response_body,"
            "elasticapm.processors.sanitize_stacktrace_locals,"
            "elasticapm.processors.sanitize_http_request_cookies,"
            "elasticapm.processors.sanitize_http_headers,"
            "elasticapm.processors.sanitize_http_wsgi_env,"
            "elasticapm.processors.sanitize_http_request_body"
        )

        self.assertEqual(processors, processors_expected)

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    @patch("serpens.elastic.ELASTIC_APM_CAPTURE_BODY", True)
    def test_setup_with_processors(self):
        processors = "elasticapm.processors.sanitize_http_headers"
        self.os_mock.environ["ELASTIC_APM_PROCESSORS"] = processors

        elastic.setup()

        self.assertEqual(self.os_mock.environ["ELASTIC_APM_PROCESSORS"], processors)

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    @patch("serpens.elastic.ELASTIC_APM_CAPTURE_BODY", True)
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

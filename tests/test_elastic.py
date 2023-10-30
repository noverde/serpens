from elasticapm.processors import MASK
from serpens import elastic
from serpens.elastic import logger, set_transaction_result
from unittest.mock import patch
import json
import unittest
from elasticapm.utils import starmatch_to_regex


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

        target = "serpens.elastic.ELASTIC_APM_RESPONSE_SANITIZE_FIELDS"
        value = elastic._get_response_sanitize_fields(True)
        self.os_sanitize_fields = patch(target, value)
        self.os_sanitize_fields.start()

    def tearDown(self):
        self.elastic_patcher.stop()
        self.os_patcher.stop()
        self.os_sanitize_fields.stop()

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
        self.assertTrue("serpens.elastic_sanitize.sanitize" in apm_processors)

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    def test_capture_response_string(self):
        bodies = [
            "Test body.",
            "[]Test body.",
            "{Test body.",
        ]

        for body in bodies:
            elastic.capture_response(body)
            self.mock_elastic.set_custom_context.assert_not_called()

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    def test_capture_response_json_string(self):
        body = '{"name":"Test", "password":12345}'
        expected = json.dumps({"name": "Test", "password": MASK})

        elastic.capture_response(body)
        self.mock_elastic.set_custom_context.assert_called_once_with({"response_body": expected})

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    def test_capture_response(self):
        body = {"name": "Test", "password": 12345}
        expected = json.dumps({"name": "Test", "password": MASK})

        elastic.capture_response(body)
        self.mock_elastic.set_custom_context.assert_called_once_with({"response_body": expected})

    def test_capture_response_disabled(self):
        body = {"name": "Test", "password": 12345}
        elastic.capture_response(body)
        self.mock_elastic.set_custom_context.assert_not_called()

    def test_get_response_sanitize_field_names(self):
        self.os_mock.environ["ELASTIC_APM_RESPONSE_SANITIZE_FIELD_NAMES"] = "password,passwd"
        field_names = ("password", "passwd")

        fields_expected = [starmatch_to_regex(x) for x in field_names]

        fields = elastic._get_response_sanitize_fields(True)

        self.assertEqual(fields, fields_expected)

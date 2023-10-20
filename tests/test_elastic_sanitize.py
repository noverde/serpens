from copy import deepcopy
from elastic_sanitize import sanitize, _sanitize_var
from elasticapm.base import Config
from elasticapm.processors import MASK
from elasticapm.utils import starmatch_to_regex
import unittest


class _ClientMock:
    def __init__(self) -> None:
        self.config = Config()


class TestElasticSanitize(unittest.TestCase):
    _client = _ClientMock()

    def test_sanitize(self):
        event = {
            "context": {
                "request": {
                    "method": "POST",
                    "body": {
                        "sid": "27d52325-099f-4565-80d2-4ed64798c72c",
                        "password": "654321",
                        "partner_id": 1,
                        "product_id": 3,
                        "event": "payment.xpto",
                        "url": "https://9574-168-205-69-207.sa.ngrok.io",
                        "secret": "123456789",
                        "data": {
                            "payment_uuid": "27d52325-099f-4565-80d2-4ed64798c72c",
                            "state": "created",
                            "details": {
                                "payment_slip_barcode": "1234567890",
                                "payment_slip_digitable_line": "1234567890987654321",
                                "password": "321312312",
                            },
                        },
                    },
                },
            },
        }
        event_expected = deepcopy(event)
        body_expected = event_expected["context"]["request"]["body"]
        body_expected["password"] = MASK
        body_expected["secret"] = MASK
        body_expected["data"]["details"]["password"] = MASK

        sanitize(self._client, event)

        self.assertDictEqual(event_expected, event)

    def test_sanitize_ignore(self):
        events = [
            {
                "context": {
                    "request": {"method": "POST", "body": "test=test&password=32312"},
                },
            },
            {"context": {"request": {"method": "POST", "body": None}}},
            {"context": {"request": {"method": "POST"}}},
            {"context": {}},
            {},
        ]
        for event in events:
            with self.subTest(use_case=event):
                event_expected = deepcopy(event)
                sanitize(self._client, event)

                self.assertDictEqual(event_expected, event)

    def test_sanitize_var_mask(self):
        fields_names_rules = ["*password*", "document"]
        fields_names = [starmatch_to_regex(x) for x in fields_names_rules]

        inputs = (
            {"key": "PASSWORD_USER", "value": "12345", "sanitize_field_names": fields_names},
            {"key": "DoCuMeNt", "value": "12345", "sanitize_field_names": fields_names},
        )

        for input in inputs:
            with self.subTest(use_case=input):
                value = _sanitize_var(**input)

                self.assertEqual(value, MASK)

    def test_sanitize_var_keep_value(self):
        fields_names_rules = ["*password*", "document"]
        fields_names = [starmatch_to_regex(x) for x in fields_names_rules]

        inputs = (
            {"key": "custom", "value": "12345", "sanitize_field_names": fields_names},
            {"key": None, "value": "12345", "sanitize_field_names": fields_names},
            {"key": "PASSWORD", "value": None, "sanitize_field_names": fields_names},
            {
                "key": "PASSWORD",
                "value": {"PASSWORD": "12345"},
                "sanitize_field_names": fields_names,
            },
        )

        for input in inputs:
            with self.subTest(use_case=input):
                previous_value = deepcopy(input["value"])
                value = _sanitize_var(**input)

                self.assertEqual(value, previous_value)

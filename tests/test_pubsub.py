import json
import unittest
from unittest.mock import patch

from google.api_core import exceptions
from pubsub import publish_message
from serpens.schema import SchemaEncoder


class pubsub(unittest.TestCase):
    @patch("pubsub.pubsub_v1")
    def test_publish_message_succeeded(self, m_pubsub_v1):
        use_cases = (
            {
                "case": "data is not an instance of string",
                "topic": "projects/myproject/topics/mytopic",
                "data": {"foo": "bar"},
                "attributes": {"foo": "bar"},
            },
            {
                "case": "attribute is none",
                "topic": "projects/myproject/topics/mytopic",
                "data": "foo",
                "attributes": None,
            },
            {
                "case": "topic name have a endpoint",
                "topic": "projects/myproject/topics/mytopic:myqueue",
                "data": "foo",
                "attributes": {"foo": "bar"},
            },
        )

        expected_message_id = 123
        publisher = m_pubsub_v1.PublisherClient.return_value
        publisher.publish.return_value.result.return_value = expected_message_id

        for case in use_cases:
            with self.subTest(case):
                message_id = publish_message(
                    case["topic"], case["data"], attributes=case["attributes"]
                )

                if not isinstance(case["data"], str):
                    case["data"] = json.dumps(case["data"], cls=SchemaEncoder)

                if case["attributes"] is None:
                    case["attributes"] = {}

                if ":" in case["topic"]:
                    case["topic"], endpoint = case["topic"].split(":")
                    case["endpoint"] = endpoint

                self.assertEqual(message_id, expected_message_id),

                publisher.publish.assert_called_with(
                    case["topic"],
                    data=case["data"].encode("utf-8"),
                    ordering_key="",
                    **case["attributes"],
                )

    @patch("pubsub.pubsub_v1")
    def test_publish_message_failed(self, m_pubsub_v1):
        attr = {"key": "value"}
        message = "message"

        publisher = m_pubsub_v1.PublisherClient.return_value
        publisher.publish.side_effect = exceptions.NotFound(
            "404 Resource not found (resource=sre-playground)"
        )

        with self.assertRaises(exceptions.NotFound):
            publish_message(
                "projects/dotz-noverde-dev/topics/sre-playground", message, attributes=attr
            )

import json
import unittest
from unittest.mock import patch

from google.api_core import exceptions
from pubsub import publish_message, publish_message_batch
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
                "ordering_key": "",
            },
            {
                "case": "attribute is none",
                "topic": "projects/myproject/topics/mytopic",
                "data": "foo",
                "attributes": None,
                "ordering_key": "",
            },
            {
                "case": "topic name have a endpoint",
                "topic": "projects/myproject/topics/mytopic:myqueue",
                "data": "foo",
                "attributes": {"foo": "bar"},
                "ordering_key": "",
            },
            {
                "case": "ordering key is none",
                "topic": "projects/myproject/topics/mytopic",
                "data": "foo",
                "attributes": {"foo": "bar"},
                "ordering_key": None,
            },
        )

        expected_message_id = 123
        publisher = m_pubsub_v1.PublisherClient.return_value
        publisher.publish.return_value.result.return_value = expected_message_id

        for case in use_cases:
            with self.subTest(**case):
                message_id = publish_message(
                    case["topic"],
                    case["data"],
                    ordering_key=case["ordering_key"],
                    attributes=case["attributes"],
                )

                if not isinstance(case["data"], str):
                    case["data"] = json.dumps(case["data"], cls=SchemaEncoder)

                if case["attributes"] is None:
                    case["attributes"] = {}

                if ":" in case["topic"]:
                    case["topic"], case["endpoint"] = case["topic"].split(":")

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
                "projects/dotz-noverde-dev/topics/sre-playground",
                message,
                attributes=attr,
            )

    @patch("pubsub.pubsub_v1")
    def test_publish_message_batch_succeeded(self, m_pubsub_v1):
        use_cases = (
            {
                "case": "data is not an instance of string",
                "topic": "projects/myproject/topics/mytopic",
                "data": [{"body": {"foo": "bar"}, "attributes": {"foo": "bar"}}],
                "ordering_key": "",
            },
            {
                "case": "attribute is none",
                "topic": "projects/myproject/topics/mytopic",
                "data": [{"body": "foo"}],
                "ordering_key": "",
            },
            {
                "case": "topic name have a endpoint",
                "topic": "projects/myproject/topics/mytopic:myqueue",
                "data": [{"body": "foo", "attributes": {"foo": "bar"}}],
                "ordering_key": "",
            },
            {
                "case": "ordering key is None",
                "topic": "projects/myproject/topics/mytopic",
                "data": [{"body": "bar", "attributes": {"foo": "bar"}}],
                "ordering_key": None,
            },
        )

        expected_message_id = 123
        publisher = m_pubsub_v1.PublisherClient.return_value
        publisher.publish.return_value.result.return_value = expected_message_id

        for case in use_cases:
            with self.subTest(**case):
                message_id = publish_message_batch(
                    case["topic"], case["data"], case["ordering_key"]
                )

                if ":" in case["topic"]:
                    case["topic"], case["endpoint"] = case["topic"].split(":")

                messages = case["data"]

                for message in messages:

                    if not isinstance(message["body"], str):
                        message["body"] = json.dumps(message["body"], cls=SchemaEncoder)

                    if message.get("attributes") is None:
                        message["attributes"] = {}

                    self.assertEqual(message_id, [123]),

                    publisher.publish.assert_called_with(
                        case["topic"],
                        data=message["body"].encode("utf-8"),
                        ordering_key="",
                        **message["attributes"],
                    )

    @patch("pubsub.pubsub_v1")
    def test_publish_message_batch_failed(self, m_pubsub_v1):
        message = [{"body": "foo", "attributes": {"foo": "bar"}}]

        publisher = m_pubsub_v1.PublisherClient.return_value
        publisher.publish.side_effect = exceptions.NotFound(
            "404 Resource not found (resource=sre-playground)"
        )

        with self.assertRaises(exceptions.NotFound):
            publish_message_batch(
                "projects/dotz-noverde-dev/topics/sre-playground",
                message,
            )

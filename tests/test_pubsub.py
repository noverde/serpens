import unittest
from unittest.mock import patch

from google.api_core import exceptions
from pubsub import publish_message


class pubsub(unittest.TestCase):
    @patch("pubsub.pubsub_v1")
    def test_publish_message_succeeded(self, m_pubsub_v1):
        expected_message_id = 123
        attr = {"key": "value"}
        message = "message"

        publisher = m_pubsub_v1.PublisherClient.return_value
        publisher.publish.return_value.result.return_value = expected_message_id

        message_id = publish_message(
            "projects/dotz-noverde-dev/topics/sre-playground", message, attributes=attr
        )

        self.assertEqual(message_id, expected_message_id),
        publisher.publish.assert_called_once_with(
            "projects/dotz-noverde-dev/topics/sre-playground",
            data=message.encode("utf-8"),
            ordering_key="",
            **attr,
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

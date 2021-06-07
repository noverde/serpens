import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

import sns
from schema import SchemaEncoder


class TestPublishMessage(unittest.TestCase):
    @patch("sns.boto3")
    def test_publish_message_succeeded(self, m_boto3):
        topic_arn = "arn:aws:sns:::test"
        message = {"message": "my message"}
        attributes = {"foo": "bar"}

        sns.publish_message(topic_arn, message, attributes)

        m_boto3.client.assert_called_once_with("sns")
        m_boto3.client.return_value.publish.assert_called_once_with(
            TargetArn=topic_arn,
            Message=json.dumps(message),
            MessageStructure="json",
            MessageAttributes=attributes,
        )


class TestNoverdeEvents(unittest.TestCase):
    def setUp(self):
        self.noverde_events = sns.NoverdeEvents(
            category="test",
            type="test",
            aggregate_id="1",
            payload={"foo": "bar"},
        )

    def test_message_property(self):
        expected = {"default": json.dumps(asdict(self.noverde_events), cls=SchemaEncoder)}

        self.assertDictEqual(self.noverde_events.message, expected)

    def test_attributes_property(self):
        expected = {"event_type": {"DataType": "String", "StringValue": self.noverde_events.type}}

        self.assertDictEqual(self.noverde_events.attributes, expected)

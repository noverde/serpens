import json
import sqs
import unittest

from datetime import datetime
from unittest.mock import patch
from sqs import Record


class TestPublishMessage(unittest.TestCase):
    @patch("sqs.boto3")
    def test_publish_message_succeeded(self, m_boto3):
        queue_url = "test.fifo"
        body = '{"message":"my message"}'
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        m_boto3.client.assert_called_once_with("sqs")
        m_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody='{"message":"my message"}',
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
        )


class TestSQSHandler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.event = {
            "Records": [
                {
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": "1627916182931",
                        "SenderId": "667031852265",
                        "ApproximateFirstReceiveTimestamp": "1627916182943",
                    },
                    "body": '{"foo":"bar"}',
                    "eventSourceARN": "arn:aws:sqs:us-east-1:667031852265:f1",
                }
            ]
        }
        cls.context = {"nothing": "here"}

    def test_handler(self):
        record = None

        @sqs.handler
        def handler(message: Record):
            nonlocal record
            record = message

        handler(self.event, self.context)

        self.assertIsInstance(record, Record)
        self.assertIsInstance(record.body, dict)
        self.assertIsInstance(record.sent_datetime, datetime)
        self.assertEqual(record.body["foo"], "bar")


class TestSQSRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.event = {
            "Records": [
                {
                    "messageId": "2b935837-2f81-42e6-a78c-07e59643526d",
                    "receiptHandle": "AQEBcnawFtnOjnQZ",
                    "body": '{"foo":"bar"}',
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": "1627916182931",
                        "SenderId": "667031852265",
                        "ApproximateFirstReceiveTimestamp": "1627916182943",
                    },
                    "messageAttributes": {
                        "cidade": {
                            "stringValue": "Manaus",
                            "stringListValues": [],
                            "binaryListValues": [],
                            "dataType": "String.nome",
                        }
                    },
                    "md5OfMessageAttributes": "b628082aeb03344d6e6c84a141e150e1",
                    "md5OfBody": "dd340d8fe79977bb0fc86da33a75ef89",
                    "eventSource": "aws:sqs",
                    "eventSourceARN": "arn:aws:sqs:us-east-1:667031852265:f1",
                    "awsRegion": "us-east-1",
                }
            ]
        }
        cls.context = {"nothing": "here"}

    def test_create_record_attrs(self):
        data = self.event["Records"][0]
        record = Record(data)

        self.assertEqual(record.body, json.loads(data["body"]))
        self.assertEqual(record.message_attributes, data["messageAttributes"])
        self.assertEqual(record.queue_name, "f1")
        self.assertIsInstance(record.sent_datetime, datetime)

    def test_create_record_data(self):
        data = self.event["Records"][0]
        record = Record(data)

        self.assertEqual(record.data["messageId"], data["messageId"])
        self.assertEqual(record.data["receiptHandle"], data["receiptHandle"])
        self.assertEqual(record.data["md5OfMessageAttributes"], data["md5OfMessageAttributes"])
        self.assertEqual(record.data["md5OfBody"], data["md5OfBody"])
        self.assertEqual(record.data["eventSource"], data["eventSource"])
        self.assertEqual(record.data["eventSourceARN"], data["eventSourceARN"])
        self.assertEqual(record.data["awsRegion"], data["awsRegion"])
        self.assertEqual(record.data["attributes"], data["attributes"])

    def test_create_record_with_body_as_str(self):
        self.event["Records"][0]["body"] = "some value"
        data = self.event["Records"][0]
        record = Record(data)

        self.assertEqual(record.body, data["body"])

    def test_create_record_with_message_attributes_as_str(self):
        self.event["Records"][0]["messageAttributes"] = '{"key": "val"}'
        data = self.event["Records"][0]
        record = Record(data)

        self.assertEqual(record.message_attributes, json.loads(data["messageAttributes"]))

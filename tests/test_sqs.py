import unittest
from unittest.mock import patch

import json
import sqs


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
                    "body": '{"foo":"bar"}',
                }
            ]
        }
        cls.context = {"nothing": "here"}

    def test_handler(self):
        record = None

        @sqs.handler
        def handler(message: sqs.Record):
            nonlocal record
            record = message

        handler(self.event, self.context)

        self.assertIsInstance(record, sqs.Record)
        self.assertIsInstance(record.body, dict)
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
                            "stringValue": "sobradinho",
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

    def test_create_record(self):
        record_raw = self.event["Records"][0]
        record = sqs.Record(
            message_id=record_raw.get("messageId", None),
            receipt_handle=record_raw.get("receiptHandle", None),
            body=record_raw.get("body", None),
            attributes=record_raw.get("attributes", None),
            message_attributes=record_raw.get("messageAttributes", None),
            md5_of_message_attributes=record_raw.get("md5OfMessageAttributes", None),
            md5_of_body=record_raw.get("md5OfBody", None),
            event_source=record_raw.get("eventSource", None),
            event_source_arn=record_raw.get("eventSourceARN", None),
            aws_region=record_raw.get("awsRegion", None),
        )
        self.assertEqual(record.message_id, record_raw["messageId"])
        self.assertEqual(record.receipt_handle, record_raw["receiptHandle"])
        self.assertEqual(record.body, json.loads(record_raw["body"]))
        self.assertEqual(record.attributes, record_raw["attributes"])
        self.assertEqual(record.message_attributes, record_raw["messageAttributes"])
        self.assertEqual(record.md5_of_message_attributes, record_raw["md5OfMessageAttributes"])
        self.assertEqual(record.md5_of_body, record_raw["md5OfBody"])
        self.assertEqual(record.event_source, record_raw["eventSource"])
        self.assertEqual(record.event_source_arn, record_raw["eventSourceARN"])
        self.assertEqual(record.aws_region, record_raw["awsRegion"])

    def test_create_record_with_body_as_str(self):
        self.event = {"Records": [{"body": "some value"}]}
        record_raw = self.event["Records"][0]
        record = sqs.Record(body=record_raw.get("body", None))
        self.assertEqual(record.body, record_raw["body"])

    def test_create_record_with_attributes_as_str(self):
        pass

    def test_create_record_with_message_attributes_as_str(self):
        pass

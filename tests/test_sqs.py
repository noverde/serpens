from datetime import datetime
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
                    "attributes": {
                        "ApproximateReceiveCount": "1",
                        "SentTimestamp": "1627916182931",
                        "SenderId": "667031852265",
                        "ApproximateFirstReceiveTimestamp": "1627916182943",
                    },
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
        self.assertIsInstance(record.attributes.sent_timestamp, datetime)
        self.assertIsInstance(
            record.attributes.approximate_first_receive_timestamp,
            datetime,
        )
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
            attributes=None,
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
        self.assertEqual(record.message_attributes, record_raw["messageAttributes"])
        self.assertEqual(record.md5_of_message_attributes, record_raw["md5OfMessageAttributes"])
        self.assertEqual(record.md5_of_body, record_raw["md5OfBody"])
        self.assertEqual(record.event_source, record_raw["eventSource"])
        self.assertEqual(record.event_source_arn, record_raw["eventSourceARN"])
        self.assertEqual(record.aws_region, record_raw["awsRegion"])

    def test_create_record_with_body_as_str(self):
        self.event = {"Records": [{"body": "some value"}]}
        record_raw = self.event["Records"][0]
        record = sqs.Record(
            message_id=None,
            receipt_handle=None,
            body=record_raw.get("body", None),
            attributes=None,
            message_attributes=None,
            md5_of_message_attributes=None,
            md5_of_body=None,
            event_source=None,
            event_source_arn=None,
            aws_region=None,
        )

        self.assertEqual(record.body, record_raw["body"])

    def test_create_record_with_message_attributes_as_str(self):
        event = {
            "Records": [
                {
                    "body": '{"foo":"bar"}',
                    "messageAttributes": '{"key": "val"}',
                }
            ]
        }
        record_raw = event["Records"][0]
        record = sqs.Record(
            message_id=None,
            receipt_handle=None,
            body=record_raw.get("body", None),
            attributes=None,
            message_attributes=record_raw.get("messageAttributes", None),
            md5_of_message_attributes=None,
            md5_of_body=None,
            event_source=None,
            event_source_arn=None,
            aws_region=None,
        )

        self.assertEqual(record.message_attributes, json.loads(record_raw["messageAttributes"]))


class TestSQSAttributes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_attrs = {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1627916182931",
            "SenderId": "667031852265",
            "ApproximateFirstReceiveTimestamp": "1627916182943",
        }

    def test_create_attribute(self):
        attributes = sqs.Attributes(
            approximate_receive_count=self.raw_attrs["ApproximateReceiveCount"],
            sent_timestamp=self.raw_attrs["SentTimestamp"],
            sender_id=self.raw_attrs["SenderId"],
            approximate_first_receive_timestamp=self.raw_attrs["ApproximateFirstReceiveTimestamp"],
        )
        self.assertEqual(attributes.approximate_receive_count, 1)
        self.assertEqual(attributes.sent_timestamp, datetime(2021, 8, 2, 11, 56, 22, 931000))
        self.assertEqual(attributes.sender_id, self.raw_attrs["SenderId"])
        self.assertEqual(
            attributes.approximate_first_receive_timestamp,
            datetime(2021, 8, 2, 11, 56, 22, 943000),
        )

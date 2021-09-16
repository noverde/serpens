import json
import sqs
import unittest

from datetime import datetime
from unittest.mock import patch
from sqs import Record, EventSourceArn, Attributes


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
        self.assertIsInstance(record.attributes.sent_timestamp, datetime)
        self.assertIsInstance(
            record.attributes.approximate_first_receive_timestamp,
            datetime,
        )
        self.assertEqual(record.body["foo"], "bar")
        self.assertIsInstance(record.event_source_arn, EventSourceArn)


class TestSQSRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.event = {
            "Records": [
                {
                    "messageId": "2b935837-2f81-42e6-a78c-07e59643526d",
                    "receiptHandle": "AQEBcnawFtnOjnQZ",
                    "body": '{"foo":"bar"}',
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

    def test_create_record(self):
        data = self.event["Records"][0]
        record = Record(data)

        self.assertEqual(record.message_id, data["messageId"])
        self.assertEqual(record.receipt_handle, data["receiptHandle"])
        self.assertEqual(record.body, json.loads(data["body"]))
        self.assertEqual(record.message_attributes, data["messageAttributes"])
        self.assertEqual(record.md5_of_message_attributes, data["md5OfMessageAttributes"])
        self.assertEqual(record.md5_of_body, data["md5OfBody"])
        self.assertEqual(record.event_source, data["eventSource"])
        self.assertEqual(record.event_source_arn.raw, data["eventSourceARN"])
        self.assertEqual(record.aws_region, data["awsRegion"])

    def test_create_record_with_body_as_str(self):
        self.event = {"Records": [{"body": "some value"}]}
        data = self.event["Records"][0]
        record = Record(data)

        self.assertEqual(record.body, data["body"])

    def test_create_record_with_message_attributes_as_str(self):
        event = {
            "Records": [
                {
                    "body": '{"foo":"bar"}',
                    "messageAttributes": '{"key": "val"}',
                }
            ]
        }
        data = event["Records"][0]
        record = Record(data)

        self.assertEqual(record.message_attributes, json.loads(data["messageAttributes"]))


class TestSQSAttributes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw_attrs = {
            "ApproximateReceiveCount": "1",
            "SentTimestamp": "1627916182931",
            "SenderId": "667031852265",
            "ApproximateFirstReceiveTimestamp": "1627916182943",
        }

    @patch("sqs.datetime")
    def test_create_attribute(self, m_datetime):
        m_datetime.fromtimestamp = datetime.utcfromtimestamp

        attributes = Attributes(self.raw_attrs)
        self.assertEqual(attributes.approximate_receive_count, 1)
        self.assertEqual(attributes.sent_timestamp, datetime(2021, 8, 2, 14, 56, 22, 931000))
        self.assertEqual(attributes.sender_id, self.raw_attrs["SenderId"])
        self.assertEqual(
            attributes.approximate_first_receive_timestamp,
            datetime(2021, 8, 2, 14, 56, 22, 943000),
        )


class TestSQSEventSourceArn(unittest.TestCase):
    def test_create(self):
        arn_raw = "arn:aws:sqs:us-east-1:667031852265:f1"
        event_source_arn = sqs.EventSourceArn(arn_raw)

        self.assertEqual(event_source_arn.raw, arn_raw)
        self.assertEqual(event_source_arn.queue_name, "f1")

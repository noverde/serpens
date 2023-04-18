import json
import unittest
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import sqs
from sqs import Record, get_attributes


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

    @patch("sqs.boto3")
    def test_publish_message_succeeded_dict_message(self, m_boto3):
        queue_url = "test.fifo"
        body = {"message": "my message"}
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        m_boto3.client.assert_called_once_with("sqs")
        m_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody='{"message": "my message"}',
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
        )

    @patch("sqs.boto3")
    def test_publish_message_succeeded_dict_message_with_encoded_value(self, m_boto3):
        queue_url = "test.fifo"
        body = {"message": "my message", "sent_at": datetime(2022, 1, 1, 1)}
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        m_boto3.client.assert_called_once_with("sqs")
        m_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody='{"message": "my message", "sent_at": "2022-01-01T01:00:00"}',
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
        )

    @patch("sqs.boto3")
    def test_publish_message_succeeded_str_message(self, m_boto3):
        queue_url = "test.fifo"
        body = "try: import antigravity"
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        m_boto3.client.assert_called_once_with("sqs")
        m_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody="try: import antigravity",
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

    def test_handler_exception(self):
        record = None

        @sqs.handler
        def handler(message: Record):
            nonlocal record
            record = message

        event = {"Records": [{"foo": "bar"}]}

        with self.assertRaises(Exception) as ex:
            handler(event, self.context)

        self.assertIsInstance(ex.exception, KeyError)


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


class TestPublishMessageBatch(unittest.TestCase):
    def setUp(self) -> None:
        self.patch_boto3 = patch("sqs.boto3")
        self.mock_boto3 = self.patch_boto3.start()
        self.response = {
            "Successful": [],
            "Failed": [],
        }

        self.messages = [
            {
                "body": "message 1",
                "attributes": {
                    "key1": "value1",
                    "key2": 123,
                    "key3": b"binary data",
                },
            },
            {
                "body": "message 2",
                "attributes": {
                    "key1": "value2",
                    "key2": "123",
                    "key3": 123456,
                },
            },
        ]

        self.queue_url = "test.fifo"

    def test_publish_message_succeeded(self):
        response = self.response

        for message in self.messages:
            uuid = str(uuid4)
            response["Successful"].append(
                {
                    "Id": uuid,
                    "MessageId": uuid,
                    "MD5OfMessageBody": message["body"],
                    "MD5OfMessageAttributes": message["attributes"],
                    "MD5OfMessageSystemAttributes": "",
                    "SequenceNumber": "",
                }
            )

        mock_publish_message_batch = self.mock_boto3.client.return_value.send_message_batch
        mock_publish_message_batch.return_value = response

        response = sqs.publish_message_batch(self.queue_url, self.messages)

        call_entries = mock_publish_message_batch.call_args.kwargs["Entries"]

        self.assertEqual(mock_publish_message_batch.call_count, 1)
        self.assertEqual(len(call_entries), 2)
        self.assertEqual(response["Failed"], [])

    def test_publish_message_fail(self):
        response = self.response

        for message in self.messages:
            uuid = str(uuid4)
            response["Failed"].append(
                {
                    "Id": uuid,
                    "MessageId": uuid,
                    "MD5OfMessageBody": message["body"],
                    "MD5OfMessageAttributes": message["attributes"],
                    "MD5OfMessageSystemAttributes": "",
                    "SequenceNumber": "",
                }
            )

        mock_publish_message_batch = self.mock_boto3.client.return_value.send_message_batch
        mock_publish_message_batch.return_value = response

        response = sqs.publish_message_batch(self.queue_url, self.messages)

        self.assertEqual(mock_publish_message_batch.call_count, 1)
        self.assertEqual(len(response["Failed"]), 2)


class TestGetAttributesFunction(unittest.TestCase):
    def test_get_attributes_success(self):

        cases = {
            "String": "this is a string",
            "Number": 123,
            "Binary": b"this is a byte",
        }

        for obj_type, obj in cases.items():
            # When the type is number StringValue should be used
            prefix_type = obj_type if obj_type != "Number" else "String"
            with self.subTest(use_case=obj_type):
                expected_response = {f"{prefix_type}Value": obj, "DataType": obj_type}

                attributes = get_attributes(obj)

                self.assertEqual(expected_response, attributes)

    def test_get_attributes_exception(self):

        obj = datetime.now()

        message = f"Invalid data type for attribute {obj}"

        with self.assertRaisesRegex(ValueError, message):
            get_attributes(obj)

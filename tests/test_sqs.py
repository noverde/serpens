import copy
import json
import unittest
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import sqs
from sqs import Record, build_message_attributes
from serpens.sentry import FilteredEvent


class TestPublishMessage(unittest.TestCase):
    def setUp(self) -> None:
        self.patch_boto3 = patch("sqs.boto3")
        self.mock_boto3 = self.patch_boto3.start()
        self.queue_url = "test.fifo"

    def tearDown(self) -> None:
        self.patch_boto3.stop()

    def test_publish_message_succeeded(self):
        queue_url = self.queue_url
        body = '{"message":"my message"}'
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        self.mock_boto3.client.assert_called_once_with("sqs")
        self.mock_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody='{"message":"my message"}',
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
        )

    def test_publish_message_succeeded_dict_message(self):
        queue_url = self.queue_url
        body = {"message": "my message"}
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        self.mock_boto3.client.assert_called_once_with("sqs")
        self.mock_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody='{"message": "my message"}',
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
        )

    def test_publish_message_succeeded_dict_message_with_encoded_value(self):
        queue_url = self.queue_url
        body = {"message": "my message", "sent_at": datetime(2022, 1, 1, 1)}
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        self.mock_boto3.client.assert_called_once_with("sqs")
        self.mock_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody='{"message": "my message", "sent_at": "2022-01-01T01:00:00"}',
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
        )

    def test_publish_message_succeeded_str_message(self):
        queue_url = self.queue_url
        body = "try: import antigravity"
        message_group_id = "group-test-id"

        sqs.publish_message(queue_url, body, message_group_id)

        self.mock_boto3.client.assert_called_once_with("sqs")
        self.mock_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody="try: import antigravity",
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
        )

    def test_publish_message_with_attributes(self):
        queue_url = self.queue_url
        body = {"key": "value"}
        message_group_id = "group-test-id"
        message_attributes = {
            "key1": "value",
            "key2": 123,
            "key3": b"binary data",
        }

        expected_message_attributes = {
            "key1": {"StringValue": "value", "DataType": "String"},
            "key2": {"StringValue": 123, "DataType": "Number"},
            "key3": {"BinaryValue": b"binary data", "DataType": "Binary"},
        }
        sqs.publish_message(queue_url, body, message_group_id, message_attributes)

        self.mock_boto3.client.assert_called_once_with("sqs")
        self.mock_boto3.client.return_value.send_message.assert_called_once_with(
            QueueUrl=queue_url,
            MessageBody=json.dumps(body),
            MessageGroupId=message_group_id,
            MessageDeduplicationId=message_group_id,
            MessageAttributes=expected_message_attributes,
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

    def test_handler_failure_return(self):
        @sqs.handler
        def handler(message: Record):
            raise FilteredEvent("Error")

        message_id = str(uuid4())
        self.event["Records"][0].update({"messageId": message_id})

        result = handler(self.event, self.context)

        self.assertIsNotNone(result["batchItemFailures"])
        failure_items = [item["itemIdentifier"] for item in result["batchItemFailures"]]
        self.assertTrue(message_id in failure_items)

        @sqs.handler
        def handler2(message: Record):
            return {"messageId": message_id}

        result = handler2(self.event, self.context)

        self.assertIsNotNone(result["batchItemFailures"])
        failure_items = [item["itemIdentifier"] for item in result["batchItemFailures"]]
        self.assertTrue(message_id in failure_items)

        import os

        os.environ["CLOUD_PROVIDER"] = "gcp"

        with self.assertRaises(FilteredEvent) as err:
            handler(self.event, self.context)

        self.assertIn("Unsupported cloud provider or invalid event data", str(err.exception))


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

    def tearDown(self) -> None:
        self.patch_boto3.stop()

    def test_publish_message_batch_succeeded(self):
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

        expected_entries = [
            {
                "MessageBody": "message 1",
                "MessageAttributes": {
                    "key1": {"StringValue": "value1", "DataType": "String"},
                    "key2": {"StringValue": 123, "DataType": "Number"},
                    "key3": {"BinaryValue": b"binary data", "DataType": "Binary"},
                },
            },
            {
                "MessageBody": "message 2",
                "MessageAttributes": {
                    "key1": {"StringValue": "value2", "DataType": "String"},
                    "key2": {"StringValue": "123", "DataType": "String"},
                    "key3": {"StringValue": 123456, "DataType": "Number"},
                },
            },
        ]

        mock_publish_message_batch = self.mock_boto3.client.return_value.send_message_batch
        mock_publish_message_batch.return_value = response

        result = sqs.publish_message_batch(self.queue_url, self.messages)

        call_entries = mock_publish_message_batch.call_args.kwargs["Entries"]

        for entry in call_entries:
            del entry["Id"]

        self.assertEqual(mock_publish_message_batch.call_count, 1)
        self.assertEqual(len(call_entries), 2)
        self.assertEqual(result[0]["Failed"], [])
        self.assertListEqual(call_entries, expected_entries)

    def test_publish_message_batch_called_more_than_once(self):
        response = self.response
        responses = []

        messages = [{"body": f"message {i}"} for i in range(30)]

        for message in messages:
            uuid = str(uuid4)
            response["Successful"].append(
                {
                    "Id": uuid,
                    "MessageId": uuid,
                    "MD5OfMessageBody": message["body"],
                    "MD5OfMessageAttributes": None,
                    "MD5OfMessageSystemAttributes": "",
                    "SequenceNumber": "",
                }
            )

        for index in range(0, len(response["Successful"]), 10):
            response_copy = copy.deepcopy(response)
            response_copy["Successful"] = response["Successful"][index : index + 10]  # noqa
            responses.append(response_copy)

        mock_publish_message_batch = self.mock_boto3.client.return_value.send_message_batch
        mock_publish_message_batch.side_effect = responses

        result = sqs.publish_message_batch(self.queue_url, messages)

        self.assertEqual(mock_publish_message_batch.call_count, 3)
        self.assertEqual(result[0]["Failed"], [])
        self.assertEqual(len(result[0]["Successful"]), 10)

    def test_publish_message_batch_fail(self):
        response = self.response

        for message in self.messages:
            uuid = str(uuid4())
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
        self.assertEqual(len(response), 1)
        self.assertEqual(len(response[0]["Failed"]), 2)


class TestBuildAttributesFunction(unittest.TestCase):
    def test_build_message_attributes(self):
        attributes = {
            "String": "this is a string",
            "Number": 123,
            "Binary": b"this is a byte",
        }
        expected_message_attributes = {
            "String": {"StringValue": "this is a string", "DataType": "String"},
            "Number": {"StringValue": 123, "DataType": "Number"},
            "Binary": {"BinaryValue": b"this is a byte", "DataType": "Binary"},
        }
        message_Attributes = build_message_attributes(attributes)

        self.assertDictEqual(expected_message_attributes, message_Attributes)

    def test_build_attributes_exception(self):
        value = datetime.now()
        attributes = {
            "Date": value,
        }

        message = f"Invalid data type for attribute {value}"

        with self.assertRaisesRegex(ValueError, message):
            build_message_attributes(attributes)

import json
import os
import unittest
from enum import Enum
from unittest.mock import patch

from serpens.messages import MessageClient


class TestMessages(unittest.TestCase):
    def setUp(self):
        self.patch_boto3 = patch("serpens.sqs.boto3")
        self.mock_boto3 = self.patch_boto3.start()
        self.sqs_client = self.mock_boto3.client.return_value

        self.patch_pubsub_v1 = patch("serpens.pubsub.pubsub_v1")
        self.mock_pubsub_v1 = self.patch_pubsub_v1.start()
        self.pubsub_client = self.mock_pubsub_v1.PublisherClient.return_value

        self.destination = "sqs.us-east-1.amazonaws.com/1234567890/default_queue.fifo"
        self.body = {"message": "my message"}
        self.attributes = {"app_name": "platform-default"}
        self.order_key = "group-test-id"

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

        self.expected_entries = [
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

    def tearDown(self):
        self.patch_boto3.stop()
        self.patch_pubsub_v1.stop()

    @patch.dict(os.environ, {"MESSAGE_PROVIDER": "sqs"})
    def test_publish_message_sqs(self):
        MessageClient.instance().publish(
            self.destination, self.body, self.order_key, self.attributes
        )

        self.sqs_client.send_message.assert_called_once_with(
            QueueUrl=self.destination,
            MessageBody='{"message": "my message"}',
            MessageAttributes={
                "app_name": {"StringValue": "platform-default", "DataType": "String"}
            },
            MessageGroupId=self.order_key,
            MessageDeduplicationId=self.order_key,
        )

    @patch.dict(os.environ, {"MESSAGE_PROVIDER": "sqs"})
    def test_publish_message_batch_sqs(self):
        MessageClient().publish_batch(self.destination, self.messages)

        call_entries = self.sqs_client.send_message_batch.call_args.kwargs["Entries"]

        for entry in call_entries:
            del entry["Id"]

        self.sqs_client.send_message_batch.assert_called_once()
        self.assertListEqual(call_entries, self.expected_entries)

    @patch.dict(os.environ, {"MESSAGE_PROVIDER": "pubsub"})
    def test_publish_message_pubsub(self):
        self.pubsub_client.publish.return_value.result.return_value = "10580991169012026"

        response = MessageClient().publish(
            self.destination, self.body, self.order_key, self.attributes
        )
        self.pubsub_client.publish.assert_called_once_with(
            self.destination,
            data=json.dumps(self.body).encode(),
            ordering_key=self.order_key,
            app_name="platform-default",
        )

        self.assertIsInstance(response, dict)

    def test_publish_message_provider_improperly_configured(self):
        with self.assertRaises(ValueError):
            MessageClient.instance().publish(
                self.destination, self.body, self.order_key, self.attributes
            )

        self.sqs_client.assert_not_called()

    def test_publish_message_provider_module_not_found(self):
        with self.assertRaises(ModuleNotFoundError):

            class MessageProvider(Enum):
                INVALID = "invalid"
                SQS = "sqs"

            MessageClient(provider=MessageProvider.INVALID).publish(
                self.destination, self.body, self.order_key, self.attributes
            )

        self.sqs_client.assert_not_called()

    @patch.dict(os.environ, {"MESSAGE_PROVIDER": "sqs"})
    def test_publish_message_singleton(self):
        client_1 = MessageClient.instance()
        client_2 = MessageClient.instance()

        self.assertEqual(id(client_1), id(client_2))

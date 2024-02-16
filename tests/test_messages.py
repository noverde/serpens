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

        self.destination = "sqs.us-east-1.amazonaws.com/1234567890/default_queue.fifo"
        self.body = {"message": "my message"}
        self.attributes = {"app_name": "platform-default"}
        self.order_key = "group-test-id"

    def tearDown(self):
        self.patch_boto3.stop()

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

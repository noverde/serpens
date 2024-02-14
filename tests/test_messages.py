import unittest
from unittest.mock import patch

import messages


class TestMessages(unittest.TestCase):
    def setUp(self):
        self.patch_boto3 = patch("sqs.boto3")
        self.mock_boto3 = self.patch_boto3.start()
        self.sqs_client = self.mock_boto3.client.return_value

        self.queue_url = "sqs.us-east-1.amazonaws.com/1234567890/default_queue.fifo"
        self.body = {"message": "my message"}
        self.attributes = {"app_name": "platform-default"}
        self.message_group_id = "group-test-id"

    def tearDown(self):
        self.patch_boto3.stop()

    @patch("messages.MESSAGE_PROVIDER", "sqs")
    def test_publish_message_sqs(self):
        messages.publish_message(self.queue_url, self.body, self.message_group_id, self.attributes)

        self.sqs_client.send_message.assert_called_once_with(
            QueueUrl=self.queue_url,
            MessageBody='{"message": "my message"}',
            MessageAttributes={
                "app_name": {"StringValue": "platform-default", "DataType": "String"}
            },
            MessageGroupId=self.message_group_id,
            MessageDeduplicationId=self.message_group_id,
        )

    def test_publish_message_provider_improperly_configured(self):
        with self.assertRaises(ValueError):
            messages.publish_message(
                self.queue_url, self.body, self.message_group_id, self.attributes
            )

        self.sqs_client.assert_not_called()

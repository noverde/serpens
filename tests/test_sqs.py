import unittest
from unittest.mock import patch

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

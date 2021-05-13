import json
import unittest
from unittest.mock import patch

import secrets


class TestSecrets(unittest.TestCase):
    @patch("secrets.boto3")
    def test_retrieve_secret_value_without_keyname(self, m_boto3):
        aws_response = {"SecretString": "s3CrE7-V@1u3"}
        m_boto3.client.return_value.get_secret_value.return_value = aws_response
        secret_value = secrets.get("Secret_Value")
        self.assertEqual(secret_value, aws_response["SecretString"])
        secrets.get("Secret_Value")
        self.assertEqual(m_boto3.client.call_count, 1)

    @patch("secrets.boto3")
    def test_retrieve_secret_value_with_keyname(self, m_boto3):
        aws_response = {"SecretString": '{"key": "s3CrE7-V@1u3"}'}
        m_boto3.client.return_value.get_secret_value.return_value = aws_response
        secret_value = secrets.get("Secret_Value", "key")
        self.assertEqual(secret_value, json.loads(aws_response["SecretString"])["key"])
        secrets.get("Secret_Value", "key")
        self.assertEqual(m_boto3.client.call_count, 1)

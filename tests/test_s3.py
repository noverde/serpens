import unittest
from unittest.mock import patch

import s3


class TestS3(unittest.TestCase):
    @patch("s3.boto3")
    def test_upload_document_succeeded(self, m_boto3):
        aws_response = {"ResponseMetadata": {"HTTPStatusCode": 200}}
        m_boto3.client.return_value.put_object.return_value = aws_response
        response = s3.upload_file(b"foo", "bar", "baz", "plain/text")

        self.assertTrue(response)

    @patch("s3.boto3")
    def test_upload_document_failed(self, m_boto3):
        aws_response = {"ResponseMetadata": {"HTTPStatusCode": 500}}
        m_boto3.client.return_value.put_object.return_value = aws_response
        response = s3.upload_file(b"foo", "bar", "baz", "plain/text")

        self.assertFalse(response)

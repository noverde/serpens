import unittest
from unittest.mock import Mock, patch

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

    @patch("s3.boto3")
    def test_get_document_succeeded(self, m_boto3):
        file_body = Mock()
        file_body.read.return_value = "abcdefghij".encode()

        aws_response = {"Body": file_body}
        m_boto3.client.return_value.get_object.return_value = aws_response
        response = s3.get_file("bar", "baz")

        self.assertIsNotNone(response)
        m_boto3.client.return_value.get_object.assert_called_once()

    @patch("s3.boto3")
    def test_exists_succeeded(self, m_boto3):
        aws_response = {
            "Contents": [
                {
                    "Key": "foo.pdf",
                    "LastModified": "",
                    "ETag": "da6342837a42ed4316d53bc2d8cebd33",
                    "Size": 15327,
                    "StorageClass": "STANDARD",
                }
            ]
        }
        m_boto3.client.return_value.list_objects_v2.return_value = aws_response
        response = s3.exists("bar", "baz")

        self.assertTrue(response)
        m_boto3.client.return_value.list_objects_v2.assert_called_once()

    @patch("s3.boto3")
    def test_get_document_exception(self, m_boto3):
        m_boto3.client.return_value.get_object.side_effect = Exception()

        response = s3.get_file("bar", "baz")
        self.assertIsNone(response)

    @patch("s3.boto3")
    def test_count_file_succeeded(self, m_boto3):
        aws_response = {
            "KeyCount": 1,
            "Contents": [
                {
                    "Key": "cnab_finaxis/2021/05/10/CBF100501.REM",
                    "StorageClass": "STANDARD",
                }
            ],
        }
        m_boto3.client.return_value.list_objects_v2.return_value = aws_response
        response = s3.count_files("smartfidc-development", "cnab_finaxis/2021/05/10/")
        self.assertTrue(response)
        m_boto3.client.return_value.list_objects_v2.assert_called_once()
        self.assertEqual(1, response)

    @patch("s3.boto3")
    def test_count_file_error(self, m_boto3):
        m_boto3.client.return_value.list_objects_v2.side_effect = Exception()

        response = s3.count_files("unreal-bucket", "2021/05/10/")
        self.assertIsNone(response)

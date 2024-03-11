import os
import unittest
from unittest.mock import patch

from serpens.storages import StorageClient


class TestStorages(unittest.TestCase):
    def setUp(self):
        self.patch_boto3 = patch("serpens.s3.boto3")
        self.mock_boto3 = self.patch_boto3.start()
        self.s3_client = self.mock_boto3.client.return_value

        self.bucket = ""
        self.key = ""

    def tearDown(self):
        self.patch_boto3.stop()

    @patch.dict(os.environ, {"STORAGE_PROVIDER": "s3"})
    def test_get_object_s3(self):
        StorageClient.instance().get(self.bucket, self.key)

        self.s3_client.get_object.assert_called_once_with(Bucket=self.bucket, Key=self.key)

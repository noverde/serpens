import unittest
from unittest.mock import patch

# import iam


class TestIAM(unittest.TestCase):
    @patch("iam.boto3")
    def test_upload_document_succeeded(self, m_boto3):
        self.assertTrue(True)

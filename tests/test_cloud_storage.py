import io
import unittest
from unittest.mock import patch

from serpens import cloud_storage


class TestCloudStorage(unittest.TestCase):

    @patch("serpens.cloud_storage.storage")
    @patch("serpens.cloud_storage.io")
    def test_get_object_succeeded(self, m_io, m_storage):

        m_io.BytesIO.return_value = io.BytesIO(b"abcdefghij")
        m_client = m_storage.Client

        response = cloud_storage.get_object("foo", "bar")
        self.assertIsNotNone(response)
        self.assertEqual(response.read(), b"abcdefghij")
        m_client.assert_called_once()

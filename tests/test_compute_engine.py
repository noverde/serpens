from http import HTTPStatus
import unittest
from unittest.mock import patch

import compute_engine
from requests import Response


class TestComputeEngineGCP(unittest.TestCase):
    def setUp(self):
        self.patch_requests = patch("compute_engine.requests")
        self.mock_requests = self.patch_requests.start()

        self.audience = "http://www.example.com"

    def tearDown(self) -> None:
        self.patch_requests.stop()

    def test_acquire_token(self):
        token = "eyJhbGciOiJSUzI1Ni.eyJhdWQiOiJodHRwczov.b25hd3MuY29tIi"

        mock_response = Response()
        mock_response.status_code = HTTPStatus.OK.value
        mock_response._content = token.encode()

        self.mock_requests.get.return_value = mock_response

        acquired_token = compute_engine.acquire_token(audience=self.audience)

        self.assertEqual(acquired_token, token)

    def test_acquire_token_fail(self):
        mock_response = Response()
        mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value

        self.mock_requests.get.return_value = mock_response

        response = compute_engine.acquire_token(audience=self.audience)
        self.assertIsNone(response)

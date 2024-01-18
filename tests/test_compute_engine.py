from http import HTTPStatus
import unittest
from unittest.mock import patch

import compute_engine
from requests import Response
from requests.exceptions import RequestException


class TestComputeEngineGCP(unittest.TestCase):
    @patch("compute_engine.requests")
    def test_acquire_token(self, m_requests):
        token = "eyJhbGciOiJSUzI1Ni.eyJhdWQiOiJodHRwczov.b25hd3MuY29tIi"
        audience = "http://www.example.com"

        mock_response = Response()
        mock_response.status_code = HTTPStatus.OK.value
        mock_response._content = token.encode()

        m_requests.get.return_value = mock_response

        acquired_token = compute_engine.acquire_token(audience=audience)

        self.assertEqual(acquired_token, token)

    @patch("compute_engine.requests")
    def test_acquire_token_fail(self, m_requests):
        audience = "http://www.example.com"

        mock_response = Response()
        mock_response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value

        m_requests.get.return_value = mock_response

        with self.assertRaises(RequestException):
            compute_engine.acquire_token(audience=audience)

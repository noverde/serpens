import json
import unittest
from unittest.mock import patch

import lambda_function
from botocore.response import StreamingBody
from io import BytesIO


class TestLambdaFunction(unittest.TestCase):
    @patch("lambda_function.boto3")
    def test_invoke_succeeded(self, m_boto3):
        payload_encoded = json.dumps({"key": "value"}).encode("utf-8")
        payload = StreamingBody(BytesIO(payload_encoded), len(payload_encoded))
        aws_response = {
            "StatusCode": 200,
            "FunctionError": "string",
            "LogResult": "string",
            "Payload": payload,
            "ExecutedVersion": "string",
        }

        m_boto3.client.return_value.invoke.return_value = aws_response

        response = lambda_function.invoke("function-test", {})

        self.assertDictEqual(response, {"key": "value"})

    @patch("lambda_function.boto3")
    def test_invoke_failed(self, m_boto3):
        payload_encoded = json.dumps({"error": "inkove error"}).encode("utf-8")
        payload = StreamingBody(BytesIO(payload_encoded), len(payload_encoded))
        aws_response = {
            "StatusCode": 500,
            "FunctionError": "string",
            "LogResult": "string",
            "Payload": payload,
            "ExecutedVersion": "string",
        }

        m_boto3.client.return_value.invoke.return_value = aws_response

        with self.assertRaises(Exception):
            response = lambda_function.invoke("function-test", {})
            self.assertDictEqual(response, {"error": "inkove error"})

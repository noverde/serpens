import json
import unittest
from unittest.mock import patch

import lambda_function
from botocore.response import StreamingBody
from io import BytesIO


@patch("lambda_function.boto3")
class TestLambdaFunction(unittest.TestCase):
    def test_invoke_succeeded(self, m_boto3):
        payload_encoded = json.dumps({"key": "value"}).encode()
        payload = StreamingBody(BytesIO(payload_encoded), len(payload_encoded))

        aws_response = {
            "ResponseMetadata": {
                "RequestId": "aae831be-0350-441f-9c0b-431e77682e44",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "date": "Wed, 10 Aug 2022 22:12:48 GMT",
                    "content-type": "application/json",
                    "content-length": "127",
                    "connection": "keep-alive",
                    "x-amzn-requestid": "aae831be-0350-441f-9c0b-431e77682e44",
                    "x-amzn-remapped-content-length": "0",
                    "x-amz-executed-version": "$LATEST",
                    "x-amzn-trace-id": "root=1-62f42d60-38e7e0ac327c5e546868cc49;sampled=0",
                },
                "RetryAttempts": 0,
            },
            "StatusCode": 200,
            "LogResult": "string",
            "Payload": payload,
            "ExecutedVersion": "$LATEST",
        }

        expected = {
            "status_code": 200,
            "error": None,
            "payload": '{"key": "value"}',
        }

        m_boto3.client.return_value.invoke.return_value = aws_response

        response = lambda_function.invoke("function-test", {})

        self.assertDictEqual(response, expected)

    def test_invoke_with_lambda_error(self, m_boto3):
        payload_encoded = json.dumps({"error": "invoke error"}).encode()
        payload = StreamingBody(BytesIO(payload_encoded), len(payload_encoded))

        aws_response = {
            "ResponseMetadata": {
                "RequestId": "aae831be-0350-441f-9c0b-431e77682e44",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "date": "Wed, 10 Aug 2022 22:12:48 GMT",
                    "content-type": "application/json",
                    "content-length": "127",
                    "connection": "keep-alive",
                    "x-amzn-requestid": "aae831be-0350-441f-9c0b-431e77682e44",
                    "x-amzn-remapped-content-length": "0",
                    "x-amz-executed-version": "$LATEST",
                    "x-amzn-trace-id": "root=1-62f42d60-38e7e0ac327c5e546868cc49;sampled=0",
                },
                "RetryAttempts": 0,
            },
            "StatusCode": 200,
            "LogResult": "string",
            "Payload": payload,
            "ExecutedVersion": "$LATEST",
            "FunctionError": "Unhandled",
        }

        expected = {
            "status_code": 200,
            "error": "Unhandled",
            "payload": '{"error": "invoke error"}',
        }

        m_boto3.client.return_value.invoke.return_value = aws_response

        response = lambda_function.invoke("function-test", {})
        self.assertDictEqual(response, expected)

    def test_invoke_with_exception(self, m_boto3):
        payload_encoded = json.dumps({"error": "invoke error"}).encode()
        payload = StreamingBody(BytesIO(payload_encoded), len(payload_encoded))

        m_boto3.client.return_value.invoke.side_effect = Exception("Error message")

        with self.assertRaises(Exception) as error:
            lambda_function.invoke("function-test", payload)
            self.assertEqual(str(error), "Error message")

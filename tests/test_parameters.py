import unittest
from unittest.mock import patch

import parameters


class TestParameters(unittest.TestCase):
    @patch("parameters.boto3")
    def test_retrieve_parameter(self, m_boto3):
        aws_response = {"Parameter": {"Value": "stored_parameter"}}
        m_boto3.client.return_value.get_parameter.return_value = aws_response
        parameter_value = parameters.get("stored_parameter")
        self.assertEqual(parameter_value, aws_response["Parameter"]["Value"])
        parameters.get("stored_parameter")
        self.assertEqual(m_boto3.client.call_count, 1)

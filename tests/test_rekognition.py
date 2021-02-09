import unittest
from unittest.mock import patch

import rekognition


class TestRekognition(unittest.TestCase):
    @patch("rekognition.boto3")
    def test_detect_faces_succeeded(self, m_boto3):
        aws_response = {
            "FaceDetails": [
                {
                    "BoundingBox": {
                        "Height": 0.18000000715255737,
                        "Left": 0.5555555820465088,
                        "Top": 0.33666667342185974,
                        "Width": 0.23999999463558197,
                    },
                    "Confidence": 100,
                    "Smile": {"Value": True, "Confidence": 100},
                    "Eyeglasses": {"Value": True, "Confidence": 100},
                }
            ],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        m_boto3.client.return_value.detect_faces.return_value = aws_response
        response = rekognition.faces_in_s3object("selfies", "face.jpg")

        self.assertIsNotNone(response)
        self.assertIsInstance(response, list)
        self.assertIsInstance(response[0], dict)

    @patch("rekognition.boto3")
    def test_detect_faces_failed(self, m_boto3):
        aws_response = {
            "FaceDetails": [],
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        m_boto3.client.return_value.detect_faces.return_value = aws_response
        response = rekognition.faces_in_s3object("selfies", "face.jpg")

        self.assertIsNotNone(response)
        self.assertIsInstance(response, list)
        self.assertEqual(len(response), 0)

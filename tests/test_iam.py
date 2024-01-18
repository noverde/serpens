import datetime
import unittest
from unittest.mock import patch

import iam
from dateutil.tz import tzutc


class TestIAM(unittest.TestCase):
    @patch("iam.boto3")
    def test_assume_role_with_web_identity(self, m_boto3):
        aws_response = {
            "Credentials": {
                "AccessKeyId": "154vc8sdffBG45W$#6f$56%W$W%V5$BWVE787Trdg",
                "SecretAccessKey": "51fd5g4sdsdffBG45W$#6f$56%W$W%V5$BWVE787Trdg",
                "SessionToken": "sdffBG45W$#6f$56%W$W%V5$BWVE787Trdg",
                "Expiration": datetime.datetime(2024, 1, 18, 15, 20, 17, tzinfo=tzutc()),
            },
            "SubjectFromWebIdentityToken": "225554488662322215444",
            "AssumedRoleUser": {
                "AssumedRoleId": "AROAYADG7OK3I5GGAIWYS:my-role-session-name",
                "Arn": "arn:aws:sts::22555448866:assumed-role/role-to-assume/my-role-session-name",
            },
            "Provider": "accounts.google.com",
            "Audience": "225554488662322215444",
            "ResponseMetadata": {
                "RequestId": "3412e653-78f1-4754-9a08-9446df59fefe",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amzn-requestid": "3412e653-78f1-4754-9a08-9446df59fefe",
                    "content-type": "text/xml",
                    "content-length": "1425",
                    "date": "Thu, 18 Jan 2024 14:20:16 GMT",
                },
                "RetryAttempts": 0,
            },
        }

        client = m_boto3.client.return_value
        client.assume_role_with_web_identity.return_value = aws_response

        role_arn = "arn:aws:iam::22555448866:role/role-to-assume"
        token = "eyJhbGciOiJSUzI1Ni.eyJhdWQiOiJodHRwczov.b25hd3MuY29tIi"
        role_session_name = "my-role-session-name"

        response = iam.assume_role_with_web_identity(
            role_arn=role_arn, token=token, role_session_name=role_session_name
        )

        self.assertIsInstance(response, dict)
        client.assume_role_with_web_identity.assert_called_once()
        client.assume_role_with_web_identity.assert_called_with(
            RoleArn=role_arn,
            WebIdentityToken=token,
            RoleSessionName=role_session_name,
            DurationSeconds=3600,
        )

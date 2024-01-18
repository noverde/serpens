import logging
import boto3

logger = logging.getLogger(__name__)


def assume_role_with_web_identity(role_arn, token, role_session_name, duration=3600):
    sts = boto3.client("sts")

    response = sts.assume_role_with_web_identity(
        RoleArn=role_arn,
        WebIdentityToken=token,
        RoleSessionName=role_session_name,
        DurationSeconds=duration,
    )

    return response

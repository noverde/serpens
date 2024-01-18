import logging
import boto3

logger = logging.getLogger(__name__)


def assume_role(role_arn, token, role_session_name, duration=3600):
    sts = boto3.client("sts")

    sts.assume_role_with_web_identity(
        RoleArn=role_arn,
        WebIdentityToken=token,
        DurationSeconds=duration,
        RoleSessionName=role_session_name,
    )

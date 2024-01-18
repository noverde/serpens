import boto3


def assume_role_with_web_identity(role_arn, token, role_session_name, duration=3600):
    sts = boto3.client("sts")

    response = sts.assume_role_with_web_identity(
        RoleArn=role_arn,
        WebIdentityToken=token,
        RoleSessionName=role_session_name,
        DurationSeconds=duration,
    )

    return response


def initialize_session_with_assume_role(role_arn, token, role_session_name):
    response = assume_role_with_web_identity(role_arn, token, role_session_name)

    session = boto3.Session(
        aws_access_key_id=response["Credentials"]["AccessKeyId"],
        aws_secret_access_key=response["Credentials"]["SecretAccessKey"],
        aws_session_token=response["Credentials"]["SessionToken"],
    )

    return session

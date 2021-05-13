import boto3

from cache import cached


@cached("parameters", 900)
def get(key) -> str:
    ssm = boto3.client("ssm")
    result = ssm.get_parameter(Name=key, WithDecryption=True)

    return result["Parameter"]["Value"]

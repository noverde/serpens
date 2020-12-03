import boto3


def get(key) -> str:
    ssm = boto3.client('ssm')
    result = ssm.get_parameter(Name=key, WithDecryption=True)

    return result['Parameter']['Value']

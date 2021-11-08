import boto3


def upload_file(data, bucket, key, content_type, acl="private"):
    client = boto3.client("s3")

    response = client.put_object(
        Body=data, Bucket=bucket, Key=key, ContentType=content_type, ACL=acl
    )

    return response["ResponseMetadata"]["HTTPStatusCode"] == 200


def get_file(bucket, key):
    client = boto3.client("s3")

    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception:
        return None

    return response.get("Body")


def exists(bucket, key):
    client = boto3.client("s3")

    response = client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)

    return "Contents" in response


def count_files(bucket, key):
    client = boto3.client("s3")
    try:
        response = client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
    except Exception:
        return None

    return response["KeyCount"]

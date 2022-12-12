import boto3


def upload_object(data, bucket, key, content_type, acl="private"):
    client = boto3.client("s3")

    response = client.put_object(
        Body=data, Bucket=bucket, Key=key, ContentType=content_type, ACL=acl
    )

    return response["ResponseMetadata"]["HTTPStatusCode"] == 200


def get_object(bucket, key):
    client = boto3.client("s3")

    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception:
        return None

    return response.get("Body")


def list_objects(bucket, key):
    client = boto3.client("s3")

    try:
        return client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
    except Exception:
        return None


def generate_presigned_url(bucket, key, period=3600):
    client = boto3.client("s3")
    try:
        return client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=period,
        )
    except Exception:
        return None


def exists(bucket, key):
    return "Contents" in list_objects(bucket, key)

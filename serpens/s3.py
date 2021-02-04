import boto3


def upload_file(data, bucket, key, content_type, acl="private"):
    client = boto3.client("s3")

    response = client.put_object(
        Body=data, Bucket=bucket, Key=key, ContentType=content_type, ACL=acl
    )

    return response["ResponseMetadata"]["HTTPStatusCode"] == 200

import boto3


def faces_in_s3object(bucket, key):
    client = boto3.client("rekognition")
    image = {"S3Object": {"Bucket": bucket, "Name": key}}
    response = client.detect_faces(Image=image, Attributes=["ALL"])

    return response.get("FaceDetails")

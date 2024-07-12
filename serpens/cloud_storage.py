import io

from google.cloud import storage


def get_object(bucket, key):
    file_obj = io.BytesIO()

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket)

    blob = bucket.blob(key)
    blob.download_to_file(file_obj)

    file_obj.seek(0)

    return file_obj


def upload_object(data, bucket, key, content_type, acl="private"):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket)
    blob = bucket.blob(key)

    blob.upload_from_string(data, content_type=content_type, predefined_acl=acl)
    return blob.exists()

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

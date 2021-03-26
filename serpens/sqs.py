import boto3


def publish_message(queue_url, body, message_group_id=None):
    client = boto3.client("sqs")
    params = {"QueueUrl": queue_url, "MessageBody": body}
    if queue_url.endswith(".fifo"):
        params["MessageGroupId"] = message_group_id
        params["MessageDeduplicationId"] = message_group_id
    response = client.send_message(**params)
    return response

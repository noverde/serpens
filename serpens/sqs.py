import boto3

def publish_message(queue_url, body):
    client = boto3.client('sqs')
    response = client.send_message(QueueUrl=queue_url, MessageBody=body)
    return response

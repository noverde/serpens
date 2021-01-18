import json

import boto3


def publish_message(topic_arn, message, attributes={}):
    sns_client = boto3.client("sns")
    response = sns_client.publish(
        TargetArn=topic_arn,
        Message=json.dumps(message),
        MessageStructure="json",
        MessageAttributes=attributes,
    )
    return response

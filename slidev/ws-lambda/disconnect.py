import os

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["CONNECTIONS_TABLE_NAME"])

ROOM = "default"


def handler(event, context):
    connection_id = event["requestContext"]["connectionId"]

    table.delete_item(
        Key={
            "room": ROOM,
            "connectionId": connection_id,
        }
    )

    return {"statusCode": 200, "body": "Disconnected"}

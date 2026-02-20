import os

import boto3

from broadcast import broadcast

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

    count = table.query(
        KeyConditionExpression="room = :r",
        ExpressionAttributeValues={":r": ROOM},
        Select="COUNT",
    )["Count"]
    broadcast(event, {"type": "viewer_count", "count": count})

    return {"statusCode": 200, "body": "Disconnected"}

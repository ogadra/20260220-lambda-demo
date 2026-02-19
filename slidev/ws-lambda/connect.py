import os
import time

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])

ROOM = "default"


def handler(event, context):
    connection_id = event["requestContext"]["connectionId"]
    query_params = event.get("queryStringParameters") or {}
    role = query_params.get("role", "viewer")

    if role not in ("presenter", "viewer"):
        role = "viewer"

    table.put_item(
        Item={
            "room": ROOM,
            "connectionId": connection_id,
            "role": role,
            "ttl": int(time.time()) + 86400,
        }
    )

    return {"statusCode": 200, "body": "Connected"}

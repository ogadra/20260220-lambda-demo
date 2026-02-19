import os
import time

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["CONNECTIONS_TABLE_NAME"])
session_table = dynamodb.Table(os.environ["SESSION_TABLE_NAME"])

ROOM = "default"
COOKIE_NAME = "slide_auth"


def _get_session_token(event):
    headers = event.get("headers") or {}
    cookie_header = headers.get("cookie") or headers.get("Cookie") or ""
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(f"{COOKIE_NAME}="):
            return part.split("=", 1)[1]
    return None


def _verify_session(token):
    if not token:
        return False
    try:
        response = session_table.get_item(Key={"token": token})
        item = response.get("Item")
        return item is not None and item.get("status") == "valid"
    except Exception:
        return False


def handler(event, context):
    connection_id = event["requestContext"]["connectionId"]

    token = _get_session_token(event)
    role = "presenter" if _verify_session(token) else "viewer"

    table.put_item(
        Item={
            "room": ROOM,
            "connectionId": connection_id,
            "role": role,
            "ttl": int(time.time()) + 86400,
        }
    )

    return {"statusCode": 200, "body": "Connected"}

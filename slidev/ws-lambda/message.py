import json
import os
import time

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
connections_table = dynamodb.Table(os.environ["CONNECTIONS_TABLE_NAME"])
poll_table = dynamodb.Table(os.environ["POLL_TABLE_NAME"])

ROOM = "default"
POLL_TTL_SECONDS = 86400  # 24 hours


def handler(event, context):
    body_str = event.get("body", "")
    try:
        body = json.loads(body_str)
    except (json.JSONDecodeError, TypeError):
        body = {}

    msg_type = body.get("type")
    if msg_type == "poll_vote":
        return handle_poll_vote(event, body)
    else:
        return handle_slide_sync(event, body_str)


def handle_slide_sync(event, body_str):
    connection_id = event["requestContext"]["connectionId"]

    response = connections_table.get_item(
        Key={"room": ROOM, "connectionId": connection_id}
    )
    sender = response.get("Item")
    if not sender or sender.get("role") != "presenter":
        return {"statusCode": 200, "body": "Ignored"}

    _broadcast(event, body_str, exclude_connection_id=connection_id)
    return {"statusCode": 200, "body": "Sent"}


def handle_poll_vote(event, body):
    connection_id = event["requestContext"]["connectionId"]
    poll_id = body.get("pollId")
    choices = body.get("choices", [])
    options = body.get("options", [])
    max_choices = body.get("maxChoices", 1)

    if not poll_id or not choices:
        return {"statusCode": 200, "body": "Invalid poll_vote"}

    ttl_value = int(time.time()) + POLL_TTL_SECONDS
    meta_key = {"pollId": poll_id, "connectionId": "META"}

    # Ensure META exists (conditional put — only if not already present)
    try:
        poll_table.put_item(
            Item={
                "pollId": poll_id,
                "connectionId": "META",
                "options": options,
                "maxChoices": max_choices,
                "votes": {},
                "ttl": ttl_value,
            },
            ConditionExpression="attribute_not_exists(pollId)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise

    # Validate max_choices against META
    meta_resp = poll_table.get_item(Key=meta_key)
    meta = meta_resp.get("Item")
    if not meta:
        return {"statusCode": 200, "body": "Poll not found"}

    meta_max_choices = meta.get("maxChoices", 1)
    if len(choices) > meta_max_choices:
        return {"statusCode": 200, "body": "Too many choices"}

    # Check for duplicate vote
    existing = poll_table.get_item(
        Key={"pollId": poll_id, "connectionId": connection_id}
    )
    if existing.get("Item"):
        return {"statusCode": 200, "body": "Already voted"}

    # Write vote record
    poll_table.put_item(
        Item={
            "pollId": poll_id,
            "connectionId": connection_id,
            "choices": choices,
            "ttl": ttl_value,
        }
    )

    # Atomic increment META votes
    for choice in choices:
        poll_table.update_item(
            Key=meta_key,
            UpdateExpression="ADD votes.#c :inc",
            ExpressionAttributeNames={"#c": choice},
            ExpressionAttributeValues={":inc": 1},
        )

    # Fetch updated META and broadcast
    updated_meta = poll_table.get_item(Key=meta_key).get("Item", {})
    # Convert Decimal to int for JSON serialization
    votes = {k: int(v) for k, v in updated_meta.get("votes", {}).items()}
    state_msg = json.dumps({
        "type": "poll_state",
        "pollId": poll_id,
        "options": updated_meta.get("options", []),
        "votes": votes,
    })

    _broadcast(event, state_msg, exclude_connection_id=None)
    return {"statusCode": 200, "body": "Voted"}


def _broadcast(event, message, exclude_connection_id=None):
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint = f"https://{domain}/{stage}"
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint)

    connections = connections_table.query(
        KeyConditionExpression="room = :r",
        ExpressionAttributeValues={":r": ROOM},
    )

    if isinstance(message, dict):
        message = json.dumps(message)

    stale = []
    for item in connections.get("Items", []):
        cid = item["connectionId"]
        if exclude_connection_id and cid == exclude_connection_id:
            continue
        try:
            apigw.post_to_connection(
                ConnectionId=cid,
                Data=message.encode("utf-8"),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "GoneException":
                stale.append(cid)
            else:
                raise

    for cid in stale:
        connections_table.delete_item(Key={"room": ROOM, "connectionId": cid})

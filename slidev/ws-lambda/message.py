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
    choice = body.get("choice")
    options = body.get("options", [])
    max_choices = body.get("maxChoices", 1)

    if not poll_id or not choice:
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

    # Check max_choices limit via existing vote count for this connection
    meta = poll_table.get_item(Key=meta_key)["Item"]
    meta_max_choices = meta.get("maxChoices", 1)

    existing_votes = poll_table.query(
        KeyConditionExpression="pollId = :pid AND begins_with(connectionId, :prefix)",
        ExpressionAttributeValues={
            ":pid": poll_id,
            ":prefix": f"{connection_id}#",
        },
    )
    if existing_votes["Count"] >= meta_max_choices:
        return {"statusCode": 200, "body": "Max choices reached"}

    # Check for duplicate vote on same choice (conditional put)
    vote_key = {"pollId": poll_id, "connectionId": f"{connection_id}#{choice}"}
    try:
        poll_table.put_item(
            Item={**vote_key, "ttl": ttl_value},
            ConditionExpression="attribute_not_exists(pollId)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"statusCode": 200, "body": "Already voted for this choice"}
        raise

    # Atomic increment META votes
    poll_table.update_item(
        Key=meta_key,
        UpdateExpression="ADD votes.#c :inc",
        ExpressionAttributeNames={"#c": choice},
        ExpressionAttributeValues={":inc": 1},
    )

    # Fetch updated META and broadcast
    updated_meta = poll_table.get_item(Key=meta_key)["Item"]
    # Convert Decimal to int for JSON serialization
    votes = {k: int(v) for k, v in updated_meta.get("votes", {}).items()}
    state_msg = json.dumps({
        "type": "poll_state",
        "pollId": poll_id,
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
        connection_id = item["connectionId"]
        if exclude_connection_id and connection_id == exclude_connection_id:
            continue
        try:
            apigw.post_to_connection(
                ConnectionId=connection_id,
                Data=message.encode("utf-8"),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "GoneException":
                stale.append(connection_id)
            else:
                raise

    for connection_id in stale:
        connections_table.delete_item(Key={"room": ROOM, "connectionId": connection_id})

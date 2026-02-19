import json
import time

import boto3
from botocore.exceptions import ClientError

from broadcast import POLL_TTL_SECONDS, broadcast, poll_table


def handle_poll_get(event, body):
    connection_id = event["requestContext"]["connectionId"]
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    if not poll_id or not visitor_id:
        return {"statusCode": 200, "body": "Invalid poll_get"}

    meta_key = {"pollId": poll_id, "connectionId": "META"}
    meta_resp = poll_table.get_item(Key=meta_key)
    meta = meta_resp.get("Item")
    if not meta:
        return {"statusCode": 200, "body": "Poll not found"}

    votes = {k: int(v) for k, v in meta.get("votes", {}).items()}

    # Look up this visitor's existing votes
    existing = poll_table.query(
        KeyConditionExpression="pollId = :pid AND begins_with(connectionId, :prefix)",
        ExpressionAttributeValues={
            ":pid": poll_id,
            ":prefix": f"{visitor_id}#",
        },
    )
    my_choices = [
        item["connectionId"].split("#", 1)[1]
        for item in existing.get("Items", [])
    ]

    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint = f"https://{domain}/{stage}"
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint)

    apigw.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps({
            "type": "poll_state",
            "pollId": poll_id,
            "votes": votes,
            "myChoices": my_choices,
        }).encode("utf-8"),
    )

    return {"statusCode": 200, "body": "OK"}


def handle_poll_vote(event, body):
    connection_id = event["requestContext"]["connectionId"]
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    choice = body.get("choice")
    options = body.get("options", [])
    max_choices = body.get("maxChoices", 1)

    if not poll_id or not visitor_id or not choice:
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
            ":prefix": f"{visitor_id}#",
        },
    )
    if existing_votes["Count"] >= meta_max_choices:
        return {"statusCode": 200, "body": "Max choices reached"}

    # Check for duplicate vote on same choice (conditional put)
    vote_key = {"pollId": poll_id, "connectionId": f"{visitor_id}#{choice}"}
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

    broadcast(event, state_msg, exclude_connection_id=None)
    return {"statusCode": 200, "body": "Voted"}


def handle_poll_unvote(event, body):
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    choice = body.get("choice")

    if not poll_id or not visitor_id or not choice:
        return {"statusCode": 200, "body": "Invalid poll_unvote"}

    vote_key = {"pollId": poll_id, "connectionId": f"{visitor_id}#{choice}"}
    meta_key = {"pollId": poll_id, "connectionId": "META"}

    # Delete the vote record (only if it exists)
    try:
        poll_table.delete_item(
            Key=vote_key,
            ConditionExpression="attribute_exists(pollId)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"statusCode": 200, "body": "Vote not found"}
        raise

    # Atomic decrement META votes
    poll_table.update_item(
        Key=meta_key,
        UpdateExpression="ADD votes.#c :dec",
        ExpressionAttributeNames={"#c": choice},
        ExpressionAttributeValues={":dec": -1},
    )

    # Fetch updated META and broadcast
    updated_meta = poll_table.get_item(Key=meta_key)["Item"]
    votes = {k: int(v) for k, v in updated_meta.get("votes", {}).items()}
    state_msg = json.dumps({
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
    })

    broadcast(event, state_msg, exclude_connection_id=None)
    return {"statusCode": 200, "body": "Unvoted"}

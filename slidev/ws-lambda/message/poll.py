import json
import time

import boto3
from botocore.exceptions import ClientError

from broadcast import POLL_TTL_SECONDS, ROOM, broadcast, connections_table, poll_table

MAX_INPUT_LEN = 256


def _validate_string(value, max_len=MAX_INPUT_LEN):
    return isinstance(value, str) and 0 < len(value) <= max_len


def _get_my_choices(poll_id, visitor_id):
    existing = poll_table.query(
        KeyConditionExpression="pollId = :pid AND begins_with(connectionId, :prefix)",
        ExpressionAttributeValues={
            ":pid": poll_id,
            ":prefix": f"{visitor_id}#",
        },
    )
    return [
        item["connectionId"].split("#", 1)[1]
        for item in existing.get("Items", [])
    ]


_apigw_client_cache = {}


def _get_apigw_client(event):
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint = f"https://{domain}/{stage}"
    if endpoint not in _apigw_client_cache:
        _apigw_client_cache[endpoint] = boto3.client(
            "apigatewaymanagementapi", endpoint_url=endpoint
        )
    return _apigw_client_cache[endpoint]


def _send_to_caller(event, payload):
    connection_id = event["requestContext"]["connectionId"]
    apigw = _get_apigw_client(event)
    apigw.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(payload).encode("utf-8"),
    )


def handle_poll_get(event, body):
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    options = body.get("options", [])
    max_choices = body.get("maxChoices", 1)
    if not _validate_string(poll_id) or not _validate_string(visitor_id):
        return {"statusCode": 200, "body": "Invalid poll_get"}

    connection_id = event["requestContext"]["connectionId"]
    meta_key = {"pollId": poll_id, "connectionId": "META"}
    meta_resp = poll_table.get_item(Key=meta_key)
    meta = meta_resp.get("Item")

    if not meta:
        # Check if the caller is a presenter
        conn_resp = connections_table.get_item(
            Key={"room": ROOM, "connectionId": connection_id}
        )
        caller = conn_resp.get("Item")

        if caller and caller.get("role") == "presenter":
            # Auto-create META for presenter
            try:
                poll_table.put_item(
                    Item={
                        "pollId": poll_id,
                        "connectionId": "META",
                        "options": options,
                        "maxChoices": max_choices,
                        "votes": {},
                    },
                    ConditionExpression="attribute_not_exists(pollId)",
                )
            except ClientError as e:
                if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise

            _send_to_caller(event, {
                "type": "poll_state",
                "pollId": poll_id,
                "votes": {},
                "myChoices": [],
            })

            # Broadcast to all viewers so they know the poll is now initialized
            broadcast(event, json.dumps({
                "type": "poll_state",
                "pollId": poll_id,
                "votes": {},
            }), exclude_connection_id=connection_id)

            return {"statusCode": 200, "body": "Poll initialized"}

        _send_to_caller(event, {
            "type": "poll_not_initialized",
            "pollId": poll_id,
        })
        return {"statusCode": 200, "body": "Poll not initialized"}

    votes = {k: int(v) for k, v in meta.get("votes", {}).items()}
    my_choices = _get_my_choices(poll_id, visitor_id)

    _send_to_caller(event, {
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
        "myChoices": my_choices,
    })

    return {"statusCode": 200, "body": "OK"}


def handle_poll_vote(event, body):
    connection_id = event["requestContext"]["connectionId"]
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    choice = body.get("choice")

    if (
        not _validate_string(poll_id)
        or not _validate_string(visitor_id)
        or not _validate_string(choice)
    ):
        return {"statusCode": 200, "body": "Invalid poll_vote"}

    ttl_value = int(time.time()) + POLL_TTL_SECONDS
    meta_key = {"pollId": poll_id, "connectionId": "META"}

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

    broadcast(event, state_msg, exclude_connection_id=connection_id)

    # Send caller their updated myChoices
    my_choices = _get_my_choices(poll_id, visitor_id)
    _send_to_caller(event, {
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
        "myChoices": my_choices,
    })

    return {"statusCode": 200, "body": "Voted"}


def handle_poll_unvote(event, body):
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    choice = body.get("choice")

    if (
        not _validate_string(poll_id)
        or not _validate_string(visitor_id)
        or not _validate_string(choice)
    ):
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

    connection_id = event["requestContext"]["connectionId"]
    broadcast(event, state_msg, exclude_connection_id=connection_id)

    # Send caller their updated myChoices
    my_choices = _get_my_choices(poll_id, visitor_id)
    _send_to_caller(event, {
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
        "myChoices": my_choices,
    })

    return {"statusCode": 200, "body": "Unvoted"}


def handle_poll_switch(event, body):
    connection_id = event["requestContext"]["connectionId"]
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    from_choice = body.get("fromChoice")
    to_choice = body.get("toChoice")

    if (
        not _validate_string(poll_id)
        or not _validate_string(visitor_id)
        or not _validate_string(from_choice)
        or not _validate_string(to_choice)
    ):
        return {"statusCode": 200, "body": "Invalid poll_switch"}

    ttl_value = int(time.time()) + POLL_TTL_SECONDS
    meta_key = {"pollId": poll_id, "connectionId": "META"}

    # Delete the old vote (conditional — must exist)
    from_key = {"pollId": poll_id, "connectionId": f"{visitor_id}#{from_choice}"}
    try:
        poll_table.delete_item(
            Key=from_key,
            ConditionExpression="attribute_exists(pollId)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return {"statusCode": 200, "body": "Old vote not found"}
        raise

    # Create the new vote (conditional — must not already exist)
    to_key = {"pollId": poll_id, "connectionId": f"{visitor_id}#{to_choice}"}
    try:
        poll_table.put_item(
            Item={**to_key, "ttl": ttl_value},
            ConditionExpression="attribute_not_exists(pollId)",
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            # Restore the old vote since new one already exists
            poll_table.put_item(Item={**from_key, "ttl": ttl_value})
            return {"statusCode": 200, "body": "Already voted for target choice"}
        raise

    # Atomic update META votes: fromChoice -1, toChoice +1
    poll_table.update_item(
        Key=meta_key,
        UpdateExpression="ADD votes.#from_c :dec, votes.#to_c :inc",
        ExpressionAttributeNames={"#from_c": from_choice, "#to_c": to_choice},
        ExpressionAttributeValues={":dec": -1, ":inc": 1},
    )

    # Fetch updated META and broadcast
    updated_meta = poll_table.get_item(Key=meta_key)["Item"]
    votes = {k: int(v) for k, v in updated_meta.get("votes", {}).items()}
    state_msg = json.dumps({
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
    })

    broadcast(event, state_msg, exclude_connection_id=connection_id)

    # Send caller their updated myChoices
    my_choices = _get_my_choices(poll_id, visitor_id)
    _send_to_caller(event, {
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
        "myChoices": my_choices,
    })

    return {"statusCode": 200, "body": "Switched"}

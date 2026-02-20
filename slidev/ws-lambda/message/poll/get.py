import json

from botocore.exceptions import ClientError

from broadcast import ROOM, broadcast, connections_table, poll_table
from poll.common import (
    get_meta,
    get_my_choices,
    get_votes_from_meta,
    send_to_caller,
    validate_string,
)


def handle_poll_get(event, body):
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    options = body.get("options", [])
    max_choices = body.get("maxChoices", 1)
    if not validate_string(poll_id) or not validate_string(visitor_id):
        return {"statusCode": 200, "body": "Invalid poll_get"}

    connection_id = event["requestContext"]["connectionId"]
    meta = get_meta(poll_id)

    if not meta:
        # Only presenters can initialize a poll
        conn_resp = connections_table.get_item(
            Key={"room": ROOM, "connectionId": connection_id}
        )
        caller = conn_resp.get("Item")

        if not caller or caller.get("role") != "presenter":
            send_to_caller(event, {
                "type": "poll_not_initialized",
                "pollId": poll_id,
            })
            return {"statusCode": 200, "body": "Poll not initialized"}

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

        # Broadcast to all connections so they know the poll is initialized
        broadcast(event, json.dumps({
            "type": "poll_state",
            "pollId": poll_id,
            "votes": {},
        }))

        return {"statusCode": 200, "body": "Poll initialized"}

    votes = get_votes_from_meta(meta)
    my_choices = get_my_choices(poll_id, visitor_id)

    send_to_caller(event, {
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
        "myChoices": my_choices,
    })

    return {"statusCode": 200, "body": "OK"}

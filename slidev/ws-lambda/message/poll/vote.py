import time

from botocore.exceptions import ClientError

from broadcast import POLL_TTL_SECONDS, poll_table
from poll.common import (
    broadcast_and_reply,
    send_poll_error,
    validate_meta_and_choices,
    validate_string,
)


def handle_poll_vote(event, body):
    connection_id = event["requestContext"]["connectionId"]
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    choice = body.get("choice")

    if (
        not validate_string(poll_id)
        or not validate_string(visitor_id)
        or not validate_string(choice)
    ):
        return {"statusCode": 200, "body": "Invalid poll_vote"}

    meta, error = validate_meta_and_choices(event, poll_id, visitor_id, [choice])
    if error:
        return error

    # Check max_choices limit
    meta_max_choices = meta.get("maxChoices", 1)
    existing_votes = poll_table.query(
        KeyConditionExpression="pollId = :pid AND begins_with(connectionId, :prefix)",
        ExpressionAttributeValues={
            ":pid": poll_id,
            ":prefix": f"{visitor_id}#",
        },
    )
    if existing_votes["Count"] >= meta_max_choices:
        send_poll_error(event, poll_id, visitor_id, "Max choices reached")
        return {"statusCode": 200, "body": "Max choices reached"}

    # Check for duplicate vote on same choice (conditional put)
    ttl_value = int(time.time()) + POLL_TTL_SECONDS
    meta_key = {"pollId": poll_id, "connectionId": "META"}
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

    broadcast_and_reply(event, poll_id, visitor_id, connection_id)
    return {"statusCode": 200, "body": "Voted"}

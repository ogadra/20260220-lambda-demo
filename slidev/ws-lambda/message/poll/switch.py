import time

from botocore.exceptions import ClientError

from broadcast import POLL_TTL_SECONDS, poll_table
from poll.common import broadcast_and_reply, validate_meta_and_choices, validate_strings


def handle_poll_switch(event, body):
    connection_id = event["requestContext"]["connectionId"]
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    from_choice = body.get("fromChoice")
    to_choice = body.get("toChoice")

    if not validate_strings(poll_id, visitor_id, from_choice, to_choice):
        return {"statusCode": 200, "body": "Invalid poll_switch"}

    _, error = validate_meta_and_choices(
        event, poll_id, visitor_id, [from_choice, to_choice]
    )
    if error:
        return error

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

    broadcast_and_reply(event, poll_id, visitor_id, connection_id)
    return {"statusCode": 200, "body": "Switched"}

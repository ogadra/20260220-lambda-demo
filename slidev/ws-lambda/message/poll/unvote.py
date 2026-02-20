from botocore.exceptions import ClientError

from broadcast import poll_table
from poll.common import broadcast_and_reply, validate_strings


def handle_poll_unvote(event, body):
    poll_id = body.get("pollId")
    visitor_id = body.get("visitorId")
    choice = body.get("choice")

    if not validate_strings(poll_id, visitor_id, choice):
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

    connection_id = event["requestContext"]["connectionId"]
    broadcast_and_reply(event, poll_id, visitor_id, connection_id)
    return {"statusCode": 200, "body": "Unvoted"}

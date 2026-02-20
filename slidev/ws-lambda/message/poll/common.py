import json

import boto3
from botocore.exceptions import ClientError

from broadcast import POLL_TTL_SECONDS, ROOM, broadcast, connections_table, poll_table

MAX_INPUT_LEN = 256


def validate_strings(*values, max_len=MAX_INPUT_LEN):
    return all(isinstance(v, str) and 0 < len(v) <= max_len for v in values)


def get_meta(poll_id):
    resp = poll_table.get_item(Key={"pollId": poll_id, "connectionId": "META"})
    return resp.get("Item")


def get_votes_from_meta(meta):
    return {k: int(v) for k, v in meta.get("votes", {}).items()}


def get_my_choices(poll_id, visitor_id):
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


def send_to_caller(event, payload):
    connection_id = event["requestContext"]["connectionId"]
    apigw = _get_apigw_client(event)
    apigw.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(payload).encode("utf-8"),
    )


def send_poll_error(event, poll_id, visitor_id, reason):
    """Send current poll state with error back to caller so loading spinners are cleared."""
    meta = get_meta(poll_id)
    votes = get_votes_from_meta(meta) if meta else {}
    my_choices = get_my_choices(poll_id, visitor_id)
    send_to_caller(event, {
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
        "myChoices": my_choices,
        "error": reason,
    })


def validate_meta_and_choices(event, poll_id, visitor_id, choices):
    """Validate META exists and all choices are valid options.

    Returns (meta, None) on success, or (None, response_dict) on failure.
    """
    meta = get_meta(poll_id)
    if not meta:
        send_poll_error(event, poll_id, visitor_id, "Poll not initialized")
        return None, {"statusCode": 200, "body": "Poll not initialized"}

    meta_options = meta.get("options", [])
    if meta_options:
        for choice in choices:
            if choice not in meta_options:
                send_poll_error(event, poll_id, visitor_id, "Invalid choice")
                return None, {"statusCode": 200, "body": "Invalid choice"}

    return meta, None


def broadcast_and_reply(event, poll_id, visitor_id, connection_id):
    """Fetch updated META, broadcast to all, and send caller their state."""
    meta = get_meta(poll_id)
    votes = get_votes_from_meta(meta)
    state_msg = json.dumps({
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
    })

    broadcast(event, state_msg, exclude_connection_id=connection_id)

    my_choices = get_my_choices(poll_id, visitor_id)
    send_to_caller(event, {
        "type": "poll_state",
        "pollId": poll_id,
        "votes": votes,
        "myChoices": my_choices,
    })

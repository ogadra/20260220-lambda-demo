import json

from poll import handle_poll_get, handle_poll_unvote, handle_poll_vote
from slide_sync import handle_slide_sync
from viewer_count import handle_viewer_count


def handler(event, context):
    body_str = event.get("body", "")
    try:
        body = json.loads(body_str)
    except (json.JSONDecodeError, TypeError):
        body = {}

    match body.get("type"):
        case "poll_vote":
            return handle_poll_vote(event, body)
        case "poll_unvote":
            return handle_poll_unvote(event, body)
        case "poll_get":
            return handle_poll_get(event, body)
        case "viewer_count":
            return handle_viewer_count(event, body)
        case _:
            return handle_slide_sync(event, body_str)

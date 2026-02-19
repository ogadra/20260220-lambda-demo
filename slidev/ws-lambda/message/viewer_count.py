import json

import boto3

from broadcast import broadcast, connections_table, ROOM


def _get_count():
    resp = connections_table.query(
        KeyConditionExpression="room = :r",
        ExpressionAttributeValues={":r": ROOM},
        Select="COUNT",
    )
    return resp.get("Count", 0)


def _send_to_caller(event, payload):
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    endpoint = f"https://{domain}/{stage}"
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint)
    connection_id = event["requestContext"]["connectionId"]
    apigw.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps(payload).encode("utf-8"),
    )


def handle_viewer_count(event, body):
    count = _get_count()
    _send_to_caller(event, {"type": "viewer_count", "count": count})
    return {"statusCode": 200, "body": "OK"}

import json
import os

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
connections_table = dynamodb.Table(os.environ["CONNECTIONS_TABLE_NAME"])
poll_table = dynamodb.Table(os.environ["POLL_TABLE_NAME"])

ROOM = "default"
POLL_TTL_SECONDS = 86400  # 24 hours


def broadcast(event, message, exclude_connection_id=None):
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

import os

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["CONNECTIONS_TABLE_NAME"])

ROOM = "default"


def handler(event, context):
    connection_id = event["requestContext"]["connectionId"]
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    body = event.get("body", "")

    # Get sender's role
    response = table.get_item(
        Key={"room": ROOM, "connectionId": connection_id}
    )
    sender = response.get("Item")
    if not sender or sender.get("role") != "presenter":
        return {"statusCode": 200, "body": "Ignored"}

    # Query all connections in the room
    connections = table.query(
        KeyConditionExpression="room = :r",
        ExpressionAttributeValues={":r": ROOM},
    )

    # Build the API Gateway Management API endpoint
    endpoint = f"https://{domain}/{stage}"
    apigw = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint)

    # Broadcast to all except sender
    stale = []
    for item in connections.get("Items", []):
        if item["connectionId"] == connection_id:
            continue
        try:
            apigw.post_to_connection(
                ConnectionId=item["connectionId"],
                Data=body.encode("utf-8"),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "GoneException":
                stale.append(item["connectionId"])
            else:
                raise

    # Clean up stale connections
    for cid in stale:
        table.delete_item(Key={"room": ROOM, "connectionId": cid})

    return {"statusCode": 200, "body": "Sent"}

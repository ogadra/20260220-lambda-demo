from broadcast import ROOM, broadcast, connections_table


def handle_slide_sync(event, body_str):
    connection_id = event["requestContext"]["connectionId"]

    response = connections_table.get_item(
        Key={"room": ROOM, "connectionId": connection_id}
    )
    sender = response.get("Item")
    if not sender or sender.get("role") != "presenter":
        return {"statusCode": 200, "body": "Ignored"}

    broadcast(event, body_str, exclude_connection_id=connection_id)
    return {"statusCode": 200, "body": "Sent"}

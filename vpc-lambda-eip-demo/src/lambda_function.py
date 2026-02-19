import socket
import urllib.request
import urllib.error

socket.setdefaulttimeout(2)


def handler(event, context):
    try:
        with urllib.request.urlopen("https://checkip.amazonaws.com") as res:
            ip = res.read().decode().strip()
    except (urllib.error.URLError, TimeoutError) as e:
        return {
            "statusCode": 500,
            "body": f"Failed to get global IP: {e}",
        }

    return {
        "statusCode": 200,
        "body": ip,
    }

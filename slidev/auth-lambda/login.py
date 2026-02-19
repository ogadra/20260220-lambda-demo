import base64
import os
import secrets
import time
from urllib.parse import parse_qs

import bcrypt
import boto3

dynamodb = boto3.resource("dynamodb")
session_table = dynamodb.Table(os.environ["SESSION_TABLE_NAME"])

# Secrets Manager からパスワードハッシュを取得（Lambda初期化時に1回だけ）
_sm = boto3.client("secretsmanager")
_secret = _sm.get_secret_value(SecretId=os.environ["SECRET_ARN"])
PASSWORD_HASH = _secret["SecretString"].encode("utf-8")

SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week
COOKIE_NAME = "slide_auth"

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Presenter Login</title>
<style>
body {{
    font-family: system-ui, sans-serif;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    margin: 0;
    background: #1a1a2e;
    color: #eee;
}}
.login-form {{
    background: #16213e;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}}
h1 {{
    margin: 0 0 1.5rem;
    font-size: 1.5rem;
}}
input[type="password"] {{
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #0f3460;
    border-radius: 4px;
    background: #1a1a2e;
    color: #eee;
    font-size: 1rem;
    box-sizing: border-box;
}}
button {{
    width: 100%;
    padding: 0.75rem;
    margin-top: 1rem;
    background: #e94560;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 1rem;
    cursor: pointer;
}}
button:hover {{
    background: #ff6b6b;
}}
.error {{
    color: #ff6b6b;
    margin-bottom: 1rem;
    font-size: 0.9rem;
}}
</style>
</head>
<body>
<form class="login-form" method="post" action="/login">
    <h1>Presenter Login</h1>
    {error_html}
    <input type="password" name="password" placeholder="Password" required autofocus />
    <button type="submit">Login</button>
</form>
</body>
</html>"""


def handler(event, context):
    method = event["requestContext"]["http"]["method"]

    if method == "GET":
        return _render_login_page()

    if method == "POST":
        return _handle_login(event)

    return {"statusCode": 405, "body": "Method Not Allowed"}


def _render_login_page(error=None):
    error_html = f'<p class="error">{error}</p>' if error else ""
    html = LOGIN_HTML.format(error_html=error_html)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": html,
    }


def _handle_login(event):
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    params = parse_qs(body)
    password = params.get("password", [None])[0]

    if not password:
        return _render_login_page(error="Password is required")

    if not bcrypt.checkpw(password.encode("utf-8"), PASSWORD_HASH):
        return _render_login_page(error="Invalid password")

    token = secrets.token_hex(32)
    ttl = int(time.time()) + SESSION_TTL_SECONDS

    session_table.put_item(
        Item={
            "token": token,
            "status": "valid",
            "ttl": ttl,
        }
    )

    cookie = (
        f"{COOKIE_NAME}={token}; "
        f"Path=/; "
        f"Max-Age={SESSION_TTL_SECONDS}; "
        f"Secure; HttpOnly; SameSite=Strict"
    )

    return {
        "statusCode": 302,
        "headers": {
            "Location": "/presenter/1",
            "Set-Cookie": cookie,
        },
        "body": "",
    }

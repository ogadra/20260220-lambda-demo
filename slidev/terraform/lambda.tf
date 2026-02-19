# --- WebSocket Lambda ---

data "archive_file" "ws" {
  for_each    = local.ws_handlers
  type        = "zip"
  source_dir  = "${path.module}/../ws-lambda/${each.key}"
  output_path = "${path.module}/../ws-lambda/${each.key}.zip"
}

resource "aws_lambda_function" "ws" {
  for_each         = local.ws_handlers
  filename         = data.archive_file.ws[each.key].output_path
  function_name    = "${var.project}-ws-${each.key}"
  role             = aws_iam_role.ws_lambda.arn
  handler          = "handler.handler"
  source_code_hash = data.archive_file.ws[each.key].output_base64sha256
  runtime          = "python3.14"
  timeout          = 10

  environment {
    variables = {
      CONNECTIONS_TABLE_NAME = aws_dynamodb_table.ws_connections.name
      SESSION_TABLE_NAME     = aws_dynamodb_table.sessions.name
      POLL_TABLE_NAME        = aws_dynamodb_table.poll_votes.name
    }
  }
}

resource "aws_lambda_permission" "ws" {
  for_each      = local.ws_handlers
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ws[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/${each.value.route_key}"
}

# --- Auth Lambda ---

data "external" "auth_lambda_hash" {
  program = ["bash", "-c", <<-EOF
    HASH=$(find "${path.module}/../auth-lambda" -type f \
      -not -name '*.zip' -not -path '*/layer/*' \
      | sort | xargs md5sum | md5sum | awk '{print $1}')
    echo "{\"md5\": \"$HASH\"}"
  EOF
  ]
}

resource "terraform_data" "bcrypt_layer_build" {
  triggers_replace = [
    data.external.auth_lambda_hash.result["md5"],
  ]

  provisioner "local-exec" {
    command     = "bash build-layer.sh"
    working_dir = "${path.module}/../auth-lambda"
  }
}

resource "aws_lambda_layer_version" "bcrypt" {
  depends_on          = [terraform_data.bcrypt_layer_build]
  filename            = "${path.module}/../auth-lambda/bcrypt-layer.zip"
  layer_name          = "${var.project}-bcrypt"
  compatible_runtimes = ["python3.14"]
  source_code_hash    = terraform_data.bcrypt_layer_build.id
}

data "archive_file" "login" {
  type        = "zip"
  source_file = "${path.module}/../auth-lambda/login.py"
  output_path = "${path.module}/../auth-lambda/login.zip"
}

resource "aws_lambda_function" "login" {
  filename         = data.archive_file.login.output_path
  function_name    = "${var.project}-login"
  role             = aws_iam_role.auth_lambda.arn
  handler          = "login.handler"
  source_code_hash = data.archive_file.login.output_base64sha256
  runtime          = "python3.14"
  timeout          = 10
  layers           = [aws_lambda_layer_version.bcrypt.arn]

  environment {
    variables = {
      SESSION_TABLE_NAME = aws_dynamodb_table.sessions.name
      SECRET_ARN         = aws_secretsmanager_secret.auth_password_hash.arn
    }
  }
}

resource "aws_lambda_permission" "login_apigw" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.login.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.login.execution_arn}/*/*/login"
}

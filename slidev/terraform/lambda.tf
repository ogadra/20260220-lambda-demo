# --- IAM ---

resource "aws_iam_role" "ws_lambda" {
  name = "${var.project}-ws-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "ws_lambda_dynamodb" {
  name = "${var.project}-ws-lambda-dynamodb"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
        ]
        Resource = aws_dynamodb_table.ws_connections.arn
      }
    ]
  })
}

resource "aws_iam_policy" "ws_lambda_apigw" {
  name = "${var.project}-ws-lambda-apigw"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "execute-api:ManageConnections"
        Resource = "${aws_apigatewayv2_api.websocket.execution_arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ws_dynamodb" {
  role       = aws_iam_role.ws_lambda.name
  policy_arn = aws_iam_policy.ws_lambda_dynamodb.arn
}

resource "aws_iam_role_policy_attachment" "ws_apigw" {
  role       = aws_iam_role.ws_lambda.name
  policy_arn = aws_iam_policy.ws_lambda_apigw.arn
}

# --- Lambda Zip ---

data "archive_file" "ws_connect" {
  type        = "zip"
  source_file = "${path.module}/../ws-lambda/connect.py"
  output_path = "${path.module}/../ws-lambda/connect.zip"
}

data "archive_file" "ws_disconnect" {
  type        = "zip"
  source_file = "${path.module}/../ws-lambda/disconnect.py"
  output_path = "${path.module}/../ws-lambda/disconnect.zip"
}

data "archive_file" "ws_message" {
  type        = "zip"
  source_file = "${path.module}/../ws-lambda/message.py"
  output_path = "${path.module}/../ws-lambda/message.zip"
}

# --- Lambda Functions ---

resource "aws_lambda_function" "ws_connect" {
  #checkov:skip=CKV_AWS_50:X-Ray tracing not needed for demo
  #checkov:skip=CKV_AWS_272:Code signing not needed for demo
  #checkov:skip=CKV_AWS_116:DLQ not needed for synchronous WebSocket handler
  #checkov:skip=CKV_AWS_115:Concurrent execution limit is managed by API Gateway throttling
  #checkov:skip=CKV_AWS_117:VPC not required for DynamoDB and API Gateway access
  #checkov:skip=CKV_AWS_173:Env vars contain no secrets
  filename         = data.archive_file.ws_connect.output_path
  function_name    = "${var.project}-ws-connect"
  role             = aws_iam_role.ws_lambda.arn
  handler          = "connect.handler"
  source_code_hash = data.archive_file.ws_connect.output_base64sha256
  runtime          = "python3.13"
  timeout          = 10

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.ws_connections.name
    }
  }

}

resource "aws_lambda_function" "ws_disconnect" {
  #checkov:skip=CKV_AWS_50:X-Ray tracing not needed for demo
  #checkov:skip=CKV_AWS_272:Code signing not needed for demo
  #checkov:skip=CKV_AWS_116:DLQ not needed for synchronous WebSocket handler
  #checkov:skip=CKV_AWS_115:Concurrent execution limit is managed by API Gateway throttling
  #checkov:skip=CKV_AWS_117:VPC not required for DynamoDB and API Gateway access
  #checkov:skip=CKV_AWS_173:Env vars contain no secrets
  filename         = data.archive_file.ws_disconnect.output_path
  function_name    = "${var.project}-ws-disconnect"
  role             = aws_iam_role.ws_lambda.arn
  handler          = "disconnect.handler"
  source_code_hash = data.archive_file.ws_disconnect.output_base64sha256
  runtime          = "python3.13"
  timeout          = 10

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.ws_connections.name
    }
  }

}

resource "aws_lambda_function" "ws_message" {
  #checkov:skip=CKV_AWS_50:X-Ray tracing not needed for demo
  #checkov:skip=CKV_AWS_272:Code signing not needed for demo
  #checkov:skip=CKV_AWS_116:DLQ not needed for synchronous WebSocket handler
  #checkov:skip=CKV_AWS_115:Concurrent execution limit is managed by API Gateway throttling
  #checkov:skip=CKV_AWS_117:VPC not required for DynamoDB and API Gateway access
  #checkov:skip=CKV_AWS_173:Env vars contain no secrets
  filename         = data.archive_file.ws_message.output_path
  function_name    = "${var.project}-ws-message"
  role             = aws_iam_role.ws_lambda.arn
  handler          = "message.handler"
  source_code_hash = data.archive_file.ws_message.output_base64sha256
  runtime          = "python3.13"
  timeout          = 10

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.ws_connections.name
    }
  }

}

# --- Lambda Permissions ---

resource "aws_lambda_permission" "ws_connect" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ws_connect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/$connect"
}

resource "aws_lambda_permission" "ws_disconnect" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ws_disconnect.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/$disconnect"
}

resource "aws_lambda_permission" "ws_message" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ws_message.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/$default"
}

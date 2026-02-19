# --- WebSocket Lambda ---

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
          "dynamodb:UpdateItem",
        ]
        Resource = [
          aws_dynamodb_table.ws_connections.arn,
          aws_dynamodb_table.sessions.arn,
          aws_dynamodb_table.poll_votes.arn,
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ws_dynamodb" {
  role       = aws_iam_role.ws_lambda.name
  policy_arn = aws_iam_policy.ws_lambda_dynamodb.arn
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

resource "aws_iam_role_policy_attachment" "ws_apigw" {
  role       = aws_iam_role.ws_lambda.name
  policy_arn = aws_iam_policy.ws_lambda_apigw.arn
}

# --- Login Lambda ---

resource "aws_iam_role" "auth_lambda" {
  name = "${var.project}-auth-lambda-role"

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

resource "aws_iam_policy" "auth_lambda" {
  name = "${var.project}-auth-lambda"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
        ]
        Resource = aws_dynamodb_table.sessions.arn
      },
      {
        Effect   = "Allow"
        Action   = "secretsmanager:GetSecretValue"
        Resource = aws_secretsmanager_secret.auth_password_hash.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "auth_lambda" {
  role       = aws_iam_role.auth_lambda.name
  policy_arn = aws_iam_policy.auth_lambda.arn
}

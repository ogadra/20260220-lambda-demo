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
        Resource = [
          aws_dynamodb_table.ws_connections.arn,
          aws_dynamodb_table.sessions.arn,
        ]
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

# --- Lambda Functions ---

data "archive_file" "ws" {
  for_each    = local.ws_handlers
  type        = "zip"
  source_file = "${path.module}/../ws-lambda/${each.key}.py"
  output_path = "${path.module}/../ws-lambda/${each.key}.zip"
}

resource "aws_lambda_function" "ws" {
  for_each         = local.ws_handlers
  filename         = data.archive_file.ws[each.key].output_path
  function_name    = "${var.project}-ws-${each.key}"
  role             = aws_iam_role.ws_lambda.arn
  handler          = "${each.key}.handler"
  source_code_hash = data.archive_file.ws[each.key].output_base64sha256
  runtime          = "python3.14"
  timeout          = 10

  environment {
    variables = {
      CONNECTIONS_TABLE_NAME = aws_dynamodb_table.ws_connections.name
      SESSION_TABLE_NAME     = aws_dynamodb_table.sessions.name
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

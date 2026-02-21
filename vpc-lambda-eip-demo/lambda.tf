resource "aws_iam_role" "lambda" {
  name = "${var.project}-lambda-role"

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

resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "main" {
  #checkov:skip=CKV_AWS_50:X-Ray tracing not needed for demo
  #checkov:skip=CKV_AWS_272:Code signing not needed for demo
  #checkov:skip=CKV_AWS_116:DLQ not needed for demo
  filename                       = data.archive_file.lambda.output_path
  function_name                  = "${var.project}-function"
  role                           = aws_iam_role.lambda.arn
  handler                        = "lambda_function.handler"
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  runtime                        = "python3.14"
  timeout                        = 10
  reserved_concurrent_executions = 3

  vpc_config {
    subnet_ids         = [aws_subnet.public.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  tags = {
    Name = "${var.project}-function"
  }
}

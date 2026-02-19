resource "aws_eip" "lambda" {
  domain = "vpc"

  tags = {
    Name = "${var.project}-eip"
  }
}

data "aws_network_interfaces" "lambda" {
  filter {
    name   = "subnet-id"
    values = [aws_subnet.public.id]
  }

  filter {
    name   = "interface-type"
    values = ["lambda"]
  }

  filter {
    name   = "group-id"
    values = [aws_security_group.lambda.id]
  }

  depends_on = [aws_lambda_function.main]
}

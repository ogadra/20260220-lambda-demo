output "eip_allocation_id" {
  value = aws_eip.lambda.allocation_id
}

output "eip_public_ip" {
  value = aws_eip.lambda.public_ip
}

output "lambda_eni_id" {
  value = one(data.aws_network_interfaces.lambda.ids)
}

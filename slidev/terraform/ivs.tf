resource "awscc_ivs_stage" "livestream" {
  name = "${var.project}-livestream"

  tags = [{
    key   = "Name"
    value = "${var.project}-livestream"
  }]
}

resource "terraform_data" "ivs_tokens" {
  triggers_replace = [awscc_ivs_stage.livestream.arn]

  provisioner "local-exec" {
    command = <<-EOT
      aws ivs-realtime create-participant-token \
        --stage-arn '${awscc_ivs_stage.livestream.arn}' \
        --capabilities '["SUBSCRIBE"]' \
        --user-id viewer --duration 20160 \
        --query 'participantToken.token' --output text \
        > ${path.module}/ivs-subscriber-token.txt

      aws ivs-realtime create-participant-token \
        --stage-arn '${awscc_ivs_stage.livestream.arn}' \
        --capabilities '["PUBLISH"]' \
        --user-id presenter --duration 20160 \
        --query 'participantToken.token' --output text \
        > ${path.module}/ivs-publisher-token.txt
    EOT
  }
}

data "local_file" "subscriber_token" {
  filename   = "${path.module}/ivs-subscriber-token.txt"
  depends_on = [terraform_data.ivs_tokens]
}

data "local_file" "publisher_token" {
  filename   = "${path.module}/ivs-publisher-token.txt"
  depends_on = [terraform_data.ivs_tokens]
}

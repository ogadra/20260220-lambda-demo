data "external" "content_hash" {
  program = ["sh", "${path.module}/content-hash.sh"]
}

resource "terraform_data" "slidev_deploy" {
  triggers_replace = [
    data.external.content_hash.result["md5"],
    terraform_data.ivs_tokens.id,
  ]

  provisioner "local-exec" {
    working_dir = "${path.module}/../content"
    command     = "VITE_IVS_PARTICIPANT_TOKEN='${trimspace(data.local_file.subscriber_token.content)}' pnpm run build"
  }

  provisioner "local-exec" {
    command = "aws s3 sync ${path.module}/../dist/ s3://${aws_s3_bucket.slidev.id}/ --delete"
  }
}

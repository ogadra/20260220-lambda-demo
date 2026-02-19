resource "terraform_data" "slidev_deploy" {
  triggers_replace = [
    filemd5("${path.module}/../content/slides.md"),
    filemd5("${path.module}/../content/package.json"),
    filemd5("${path.module}/../content/style.css"),
  ]

  provisioner "local-exec" {
    working_dir = "${path.module}/../content"
    command     = "pnpm install && pnpm run build"
  }

  provisioner "local-exec" {
    command = "aws s3 sync ${path.module}/../dist/ s3://${aws_s3_bucket.slidev.id}/ --delete"
  }
}

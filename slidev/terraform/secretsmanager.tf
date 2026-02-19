resource "aws_secretsmanager_secret" "auth_password_hash" {
  #checkov:skip=CKV2_AWS_57:Auto rotation not applicable for static password hash
  name = "${var.project}-auth-password-hash"
}

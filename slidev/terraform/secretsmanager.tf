resource "aws_secretsmanager_secret" "auth_password_hash" {
  #checkov:skip=CKV2_AWS_57:Auto rotation not applicable for static password hash
  #checkov:skip=CKV_AWS_149:KMS CMK not needed for demo, using default AWS managed key
  name = "${var.project}-auth-password-hash"
}

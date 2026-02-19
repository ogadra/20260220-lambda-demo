resource "aws_dynamodb_table" "ws_connections" {
  #checkov:skip=CKV_AWS_28:PITR not needed for ephemeral connection tracking
  #checkov:skip=CKV_AWS_119:KMS encryption not needed for demo
  #checkov:skip=CKV2_AWS_16:Auto scaling not needed for on-demand table
  name         = "${var.project}-ws-connections"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "room"
  range_key    = "connectionId"

  attribute {
    name = "room"
    type = "S"
  }

  attribute {
    name = "connectionId"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

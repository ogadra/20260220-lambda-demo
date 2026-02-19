resource "aws_dynamodb_table" "ws_connections" {
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

resource "aws_dynamodb_table" "poll_votes" {
  name         = "${var.project}-poll-votes"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pollId"
  range_key    = "connectionId"

  attribute {
    name = "pollId"
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

resource "aws_dynamodb_table" "sessions" {
  name         = "${var.project}-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "token"

  attribute {
    name = "token"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

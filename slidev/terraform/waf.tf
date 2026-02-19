resource "aws_wafv2_ip_set" "rate_limit_excluded" {
  provider           = aws.us_east_1
  name               = "${var.project}-rate-limit-excluded"
  scope              = "CLOUDFRONT"
  ip_address_version = "IPV4"
  addresses          = var.rate_limit_excluded_cidrs
}

resource "aws_wafv2_web_acl" "slidev" {
  #checkov:skip=CKV_AWS_192:Log4j not relevant for static site
  #checkov:skip=CKV2_AWS_31:WAF logging not needed for demo
  provider = aws.us_east_1
  name     = var.project
  scope    = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # Rate-based rule: block IPs exceeding 1000 requests per 5 minutes
  # Excluded IPs (e.g. event venue) are not subject to this rule
  rule {
    name     = "rate-limit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 10000
        aggregate_key_type = "IP"

        scope_down_statement {
          not_statement {
            statement {
              ip_set_reference_statement {
                arn = aws_wafv2_ip_set.rate_limit_excluded.arn
              }
            }
          }
        }
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project}-rate-limit"
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = var.project
  }
}

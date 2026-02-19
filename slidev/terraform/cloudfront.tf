data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_origin_access_control" "slidev" {
  name                              = var.project
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "slidev" {
  #checkov:skip=CKV_AWS_86:Access logging not needed for demo
  #checkov:skip=CKV_AWS_310:Origin failover not needed for single-origin static site
  #checkov:skip=CKV_AWS_374:Geo restriction not needed for public slides
  #checkov:skip=CKV_AWS_174:Using TLSv1.2_2021 with ACM certificate
  #checkov:skip=CKV2_AWS_32:Response headers policy not needed for demo
  #checkov:skip=CKV2_AWS_47:Log4j not relevant for static site
  enabled             = true
  aliases             = [var.custom_domain]
  default_root_object = "index.html"
  web_acl_id          = aws_wafv2_web_acl.slidev.arn

  origin {
    domain_name              = aws_s3_bucket.slidev.bucket_regional_domain_name
    origin_id                = aws_s3_bucket.slidev.id
    origin_access_control_id = aws_cloudfront_origin_access_control.slidev.id
  }

  origin {
    domain_name = "${aws_apigatewayv2_api.websocket.id}.execute-api.ap-northeast-1.amazonaws.com"
    origin_id   = "websocket-api"
    origin_path = "/production"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # WebSocket API Gateway behavior
  ordered_cache_behavior {
    path_pattern           = "/ws"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "PATCH", "POST", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "websocket-api"
    viewer_protocol_policy = "https-only"
    compress               = false

    cache_policy_id          = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = aws_s3_bucket.slidev.id
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    default_ttl = 60
    min_ttl     = 0
    max_ttl     = 86400

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }

  # SPA routing: 403/404 -> /index.html
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 60
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 60
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.slidev.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

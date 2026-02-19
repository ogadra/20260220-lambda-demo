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
  #checkov:skip=CKV_AWS_174:Default CloudFront certificate does not support custom TLS config
  #checkov:skip=CKV2_AWS_42:Using default CloudFront certificate for demo
  #checkov:skip=CKV2_AWS_32:Response headers policy not needed for demo
  #checkov:skip=CKV2_AWS_47:Log4j not relevant for static site
  enabled             = true
  default_root_object = "index.html"
  web_acl_id          = aws_wafv2_web_acl.slidev.arn

  origin {
    domain_name              = aws_s3_bucket.slidev.bucket_regional_domain_name
    origin_id                = aws_s3_bucket.slidev.id
    origin_access_control_id = aws_cloudfront_origin_access_control.slidev.id
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
    cloudfront_default_certificate = true
  }
}

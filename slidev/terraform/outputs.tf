output "cloudfront_distribution_domain" {
  description = "CloudFront distribution domain name"
  value       = aws_cloudfront_distribution.slidev.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.slidev.id
}

output "s3_bucket_name" {
  description = "S3 bucket name for file sync"
  value       = aws_s3_bucket.slidev.id
}

output "slidev_url" {
  description = "Slidev presentation URL"
  value       = "https://${aws_cloudfront_distribution.slidev.domain_name}/"
}

output "acm_dns_validation_records" {
  description = "DNS records to add in Cloudflare for ACM certificate validation"
  value = {
    for dvo in aws_acm_certificate.slidev.domain_validation_options : dvo.domain_name => {
      type  = dvo.resource_record_type
      name  = dvo.resource_record_name
      value = dvo.resource_record_value
    }
  }
}

output "custom_domain" {
  description = "Custom domain name for the CloudFront distribution"
  value       = var.custom_domain
}

output "custom_domain_cname_target" {
  description = "CNAME target for the custom domain (point your DNS to this value)"
  value       = aws_cloudfront_distribution.slidev.domain_name
}

output "ivs_stage_arn" {
  description = "IVS Real-Time stage ARN"
  value       = awscc_ivs_stage.livestream.arn
}

output "ivs_whip_server" {
  description = "WHIP server URL for OBS"
  value       = "https://global.whip.live-video.net"
}

output "ivs_publisher_token" {
  description = "OBS の Bearer Token に設定する"
  value       = trimspace(data.local_file.publisher_token.content)
  sensitive   = true
}

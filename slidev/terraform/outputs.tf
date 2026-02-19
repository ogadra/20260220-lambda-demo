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

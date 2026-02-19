resource "aws_s3_bucket" "slidev" {
  #checkov:skip=CKV_AWS_21:Versioning not needed for build artifacts
  #checkov:skip=CKV_AWS_144:Cross-region replication not needed for demo
  #checkov:skip=CKV2_AWS_61:Lifecycle config not needed, managed by s3 sync --delete
  #checkov:skip=CKV2_AWS_62:Event notifications not needed for demo
  #checkov:skip=CKV_AWS_145:SSE-S3 default encryption sufficient for public slides
  #checkov:skip=CKV_AWS_18:Access logging not needed for demo
  bucket_prefix = var.project
}

resource "aws_s3_bucket_public_access_block" "slidev" {
  bucket = aws_s3_bucket.slidev.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "slidev" {
  bucket = aws_s3_bucket.slidev.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOAC"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.slidev.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.slidev.arn
          }
        }
      }
    ]
  })
}

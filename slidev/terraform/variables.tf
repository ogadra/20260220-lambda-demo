variable "project" {
  description = "Project name used for resource naming"
  type        = string
  default     = "slidev-hosting"
}

variable "custom_domain" {
  description = "Custom domain name for CloudFront distribution (e.g. slides.example.com)"
  type        = string
}

variable "rate_limit_excluded_cidrs" {
  description = "List of CIDRs excluded from WAF rate limiting (e.g. event venue IP)"
  type        = list(string)
  default     = []
}

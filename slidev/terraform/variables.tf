variable "project" {
  description = "Project name used for resource naming"
  type        = string
  default     = "slidev-hosting"
}

variable "rate_limit_excluded_cidrs" {
  description = "List of CIDRs excluded from WAF rate limiting (e.g. event venue IP)"
  type        = list(string)
  default     = []
}

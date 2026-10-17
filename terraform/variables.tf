variable "region" {
  description = "Everything runs in London (N2)"
  type        = string
  default     = "eu-west-2"
}

variable "name" {
  type    = string
  default = "governed-rag"
}

variable "github_oidc_subject" {
  description = "GitHub's OIDC subject prefix for this repository, e.g. repo:<owner>@<id>/<repo>@<id>"
  type        = string
}

variable "alert_email" {
  description = "Where budget alerts go. Passed at apply time, never committed. Empty: no budget yet"
  type        = string
  default     = ""
}

variable "budget_limit_usd" {
  type    = number
  default = 10
}

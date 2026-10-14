variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Region for Learner Lab deployment"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Deployment environment name"
}

variable "alert_email" {
  type        = string
  default     = "pranit.mathur2024@vitstudent.ac.in"
  description = "Notification email for SLA breach and retraining alerts"
}

variable "lab_role_arn" {
  type        = string
  default     = ""
  description = "Pre-existing Learner Lab IAM Role ARN (e.g., arn:aws:iam::ACCOUNT_ID:role/LabRole). Leave empty to auto-lookup 'LabRole'."
}

variable "enable_expensive_core" {
  type        = bool
  default     = false
  description = "Flag to enable Phase 2 expensive resources (Aurora, RDS Proxy). Set true only during active sessions."
}

# ── Phase 2 DB Credentials (pass via CLI or terraform.tfvars — NEVER commit) ──

variable "db_master_username" {
  type        = string
  default     = "caqi_admin"
  description = "Aurora master username"
}

variable "db_master_password" {
  type        = string
  sensitive   = true
  description = "Aurora master password. Pass via -var or terraform.tfvars (never commit). Min 8 chars, no @, /, or spaces."
}

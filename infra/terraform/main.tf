terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CAQI"
      Environment = "AWS-Learner-Lab"
      ManagedBy   = "Terraform"
      Course      = "BCSE355L"
    }
  }
}

# ── Data sources used across modules ──
# NOTE: data "aws_caller_identity" "current" is declared in kms.tf

data "aws_iam_role" "lab_role" {
  # Learner Lab pre-creates "LabRole" — we reference it rather than creating a new one.
  # If lab_role_arn is explicitly supplied, we still look up by name (the data source
  # is always used for the role_arn reference in rds_proxy.tf).
  # Used by rds_proxy.tf for the proxy's role_arn.
  name = "LabRole"
}

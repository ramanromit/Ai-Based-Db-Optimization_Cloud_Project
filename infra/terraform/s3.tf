# 1.4 S3 Buckets

# Explainability Logs Bucket
resource "aws_s3_bucket" "explainability_logs" {
  bucket              = "caqi-explainability-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy       = true
  object_lock_enabled = false

  lifecycle {
    ignore_changes = [
      object_lock_configuration,
      object_lock_enabled,
    ]
  }

  tags = {
    Name = "caqi-explainability-logs"
  }
}

resource "aws_s3_bucket_versioning" "explainability_logs_versioning" {
  bucket = aws_s3_bucket.explainability_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "explainability_logs_encryption" {
  bucket = aws_s3_bucket.explainability_logs.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.caqi_cmk.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

# CloudTrail Logs Bucket
resource "aws_s3_bucket" "cloudtrail_logs" {
  bucket              = "caqi-cloudtrail-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy       = true
  object_lock_enabled = false

  lifecycle {
    ignore_changes = [
      object_lock_configuration,
      object_lock_enabled,
    ]
  }

  tags = {
    Name = "caqi-cloudtrail-logs"
  }
}

resource "aws_s3_bucket_policy" "cloudtrail_logs_policy" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudtrail_logs.arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudtrail_logs.arn}/prefix/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

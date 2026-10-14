# 1.9 CloudTrail

resource "aws_cloudtrail" "caqi_trail" {
  name                          = "caqi-audit-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail_logs.id
  s3_key_prefix                 = "prefix"
  include_global_service_events = true
  is_multi_region_trail         = false
  enable_log_file_validation    = true

  depends_on = [aws_s3_bucket_policy.cloudtrail_logs_policy]

  tags = {
    Name = "caqi-audit-trail"
  }
}


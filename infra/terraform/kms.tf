# 1.10 KMS Key for Encryption

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "caqi_cmk" {
  description             = "CAQI Customer Managed Key for S3 and Aurora storage encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = {
    Name = "caqi-cmk"
  }
}

resource "aws_kms_alias" "caqi_cmk_alias" {
  name          = "alias/caqi-cmk"
  target_key_id = aws_kms_key.caqi_cmk.key_id
}


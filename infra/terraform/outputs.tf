output "vpc_id" {
  value       = aws_vpc.caqi_vpc.id
  description = "CAQI VPC ID"
}

output "public_subnet_ids" {
  value       = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  description = "Public Subnet IDs"
}

output "private_subnet_ids" {
  value       = [aws_subnet.private_1.id, aws_subnet.private_2.id]
  description = "Private Subnet IDs (Aurora, RDS Proxy)"
}

output "kms_key_arn" {
  value       = aws_kms_key.caqi_cmk.arn
  description = "KMS Customer Managed Key ARN"
}

output "explainability_logs_bucket" {
  value       = aws_s3_bucket.explainability_logs.id
  description = "Explainability Logs S3 Bucket Name"
}

output "cloudtrail_logs_bucket" {
  value       = aws_s3_bucket.cloudtrail_logs.id
  description = "CloudTrail Logs S3 Bucket Name"
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.idempotency_keys.name
  description = "DynamoDB Idempotency Table Name"
}

output "sqs_queue_url" {
  value       = aws_sqs_queue.explainability_queue.url
  description = "SQS Explainability Queue URL"
}

output "sns_topic_arn" {
  value       = aws_sns_topic.caqi_alerts.arn
  description = "SNS Alert Topic ARN"
}

# ── Phase 2 Outputs (only populated when enable_expensive_core = true) ──

output "aurora_writer_endpoint" {
  value       = length(aws_rds_cluster.aurora_cluster) > 0 ? aws_rds_cluster.aurora_cluster[0].endpoint : "DISABLED"
  description = "Aurora Writer Endpoint (direct — use only for schema migration, not app traffic)"
}

output "aurora_reader_endpoint" {
  value       = length(aws_rds_cluster.aurora_cluster) > 0 ? aws_rds_cluster.aurora_cluster[0].reader_endpoint : "DISABLED"
  description = "Aurora Reader Endpoint — used by backend reader_engine for analytical/settlement queries"
}

output "rds_proxy_endpoint" {
  value       = length(aws_db_proxy.caqi_rds_proxy) > 0 ? aws_db_proxy.caqi_rds_proxy[0].endpoint : "DISABLED"
  description = "RDS Proxy Endpoint — ALL writer traffic routes through this, never Aurora directly"
}

output "db_secret_arn" {
  value       = length(aws_secretsmanager_secret.db_credentials) > 0 ? aws_secretsmanager_secret.db_credentials[0].arn : "DISABLED"
  description = "Secrets Manager ARN for Aurora master credentials"
  sensitive   = true
}

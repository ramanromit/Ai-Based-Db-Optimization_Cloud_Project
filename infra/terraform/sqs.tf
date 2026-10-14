# 1.6 SQS Queue

resource "aws_sqs_queue" "explainability_queue" {
  name                       = "caqi-explainability-events"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 10     # Long polling
  visibility_timeout_seconds = 30

  tags = {
    Name = "caqi-explainability-events"
  }
}


# 1.8 CloudWatch Metric Alarm

resource "aws_cloudwatch_metric_alarm" "auth_p99_breach" {
  alarm_name          = "caqi-auth-p99-sla-breach"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "AuthP99LatencyMs"
  namespace           = "CAQI/PaymentMetrics"
  period              = 60
  statistic           = "Maximum"
  threshold           = 10.0
  alarm_description   = "Triggers when Auth-Critical P99 latency exceeds 10.0ms budget for 2 consecutive minutes"
  alarm_actions       = [aws_sns_topic.caqi_alerts.arn]
  ok_actions          = [aws_sns_topic.caqi_alerts.arn]

  tags = {
    Name = "caqi-auth-p99-alarm"
  }
}


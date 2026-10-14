# 1.7 SNS Alert Topic & Email Subscription

resource "aws_sns_topic" "caqi_alerts" {
  name = "caqi-alerts-topic"

  tags = {
    Name = "caqi-alerts-topic"
  }
}

resource "aws_sns_topic_subscription" "email_alerts" {
  topic_arn = aws_sns_topic.caqi_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}


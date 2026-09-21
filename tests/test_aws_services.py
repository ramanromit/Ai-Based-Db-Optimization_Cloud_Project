import os
import pytest
from aws_services.cloudwatch_reporter import CloudWatchReporter, cloudwatch_reporter
from aws_services.dynamodb_client import DynamoDBClient, dynamodb_client
from aws_services.sqs_client import SQSClient, sqs_client
from aws_services.sns_client import SNSClient, sns_client

def test_cloudwatch_reporter_offline():
    reporter = CloudWatchReporter()
    assert reporter.use_aws is False
    res = reporter.push_metrics(auth_p99_ms=4.5, violation_rate=0.0, throughput_reward=0.95)
    assert res is False

def test_dynamodb_client_offline():
    client = DynamoDBClient()
    assert client.use_aws is False
    assert client.get_idempotency_key("test_key") is None
    assert client.put_idempotency_key("test_key", {"account_id": "acc_123"}) is False

def test_sqs_client_offline():
    client = SQSClient()
    assert client.use_aws is False
    assert client.send_explainability_event({"test": "data"}) is False

def test_sns_client_offline():
    client = SNSClient()
    assert client.use_aws is False
    assert client.publish_retrain_event("PROMOTED", "v1.0", {"auth_p99_ms": 4.2}) is False


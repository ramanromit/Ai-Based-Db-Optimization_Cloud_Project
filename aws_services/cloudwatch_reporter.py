import os
import logging
from typing import Optional

logger = logging.getLogger("caqi.aws.cloudwatch")

class CloudWatchReporter:
    def __init__(self):
        self.use_aws = os.getenv("USE_AWS", "false").lower() == "true"
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.namespace = os.getenv("CLOUDWATCH_NAMESPACE", "CAQI/PaymentMetrics")
        self._client = None

        if self.use_aws:
            try:
                import boto3
                self._client = boto3.client("cloudwatch", region_name=self.region)
                logger.info(f"CloudWatchReporter initialized for namespace {self.namespace}")
            except Exception as e:
                logger.warning(f"Could not initialize boto3 CloudWatch client: {e}")

    def push_metrics(self, auth_p99_ms: float, violation_rate: float, throughput_reward: float) -> bool:
        if not self._client:
            return False

        try:
            self._client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[
                    {
                        "MetricName": "AuthP99LatencyMs",
                        "Value": float(auth_p99_ms),
                        "Unit": "Milliseconds",
                        "StorageResolution": 60
                    },
                    {
                        "MetricName": "ConstraintViolationRate",
                        "Value": float(violation_rate),
                        "Unit": "Percent",
                        "StorageResolution": 60
                    },
                    {
                        "MetricName": "ThroughputReward",
                        "Value": float(throughput_reward),
                        "Unit": "None",
                        "StorageResolution": 60
                    }
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to push CloudWatch metrics: {e}")
            return False

cloudwatch_reporter = CloudWatchReporter()


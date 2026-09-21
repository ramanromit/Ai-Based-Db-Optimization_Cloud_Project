import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("caqi.aws.sns")

class SNSClient:
    def __init__(self):
        self.use_aws = os.getenv("USE_AWS", "false").lower() == "true"
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.topic_arn = os.getenv("SNS_TOPIC_ARN", "")
        self._client = None

        if self.use_aws and self.topic_arn:
            try:
                import boto3
                self._client = boto3.client("sns", region_name=self.region)
                logger.info(f"SNSClient initialized for topic {self.topic_arn}")
            except Exception as e:
                logger.warning(f"Could not initialize boto3 SNS client: {e}")

    def publish_retrain_event(self, status: str, version: str, details: Dict[str, Any]) -> bool:
        if not self._client or not self.topic_arn:
            return False
        try:
            subject = f"[CAQI ALERT] Policy Retrain Event: {status}"
            message = (
                f"CAQI Autonomous Retraining Notification\n"
                f"Status: {status}\n"
                f"Policy Version: {version}\n"
                f"Metrics: {json.dumps(details, indent=2)}\n"
            )
            self._client.publish(
                TopicArn=self.topic_arn,
                Subject=subject,
                Message=message
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish SNS retrain event: {e}")
            return False

sns_client = SNSClient()


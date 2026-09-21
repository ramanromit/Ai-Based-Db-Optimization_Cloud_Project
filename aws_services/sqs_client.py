import os
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("caqi.aws.sqs")

class SQSClient:
    def __init__(self):
        self.use_aws = os.getenv("USE_AWS", "false").lower() == "true"
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.queue_url = os.getenv("SQS_QUEUE_URL", "")
        self._client = None

        if self.use_aws and self.queue_url:
            try:
                import boto3
                self._client = boto3.client("sqs", region_name=self.region)
                logger.info(f"SQSClient initialized for queue {self.queue_url}")
            except Exception as e:
                logger.warning(f"Could not initialize boto3 SQS client: {e}")

    def send_explainability_event(self, record: Dict[str, Any]) -> bool:
        if not self._client or not self.queue_url:
            return False
        try:
            self._client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(record)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send SQS explainability event: {e}")
            return False

sqs_client = SQSClient()


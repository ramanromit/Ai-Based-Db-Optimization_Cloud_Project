import os
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("caqi.aws.dynamodb")

class DynamoDBClient:
    def __init__(self):
        self.use_aws = os.getenv("USE_AWS", "false").lower() == "true"
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.table_name = os.getenv("DYNAMODB_TABLE", "caqi-idempotency-keys")
        self._table = None

        if self.use_aws:
            try:
                import boto3
                dynamodb = boto3.resource("dynamodb", region_name=self.region)
                self._table = dynamodb.Table(self.table_name)
                logger.info(f"DynamoDBClient initialized for table {self.table_name}")
            except Exception as e:
                logger.warning(f"Could not initialize boto3 DynamoDB table: {e}")

    def get_idempotency_key(self, key: str) -> Optional[Dict[str, Any]]:
        if not self._table:
            return None
        try:
            res = self._table.get_item(Key={"idempotency_key": key})
            item = res.get("Item")
            if item:
                # Check TTL manually if item exists
                if "expires_at" in item and time.time() > float(item["expires_at"]):
                    return None
            return item
        except Exception as e:
            logger.error(f"Failed to fetch idempotency key {key}: {e}")
            return None

    def put_idempotency_key(self, key: str, payload_meta: dict, ttl_seconds: int = 86400) -> bool:
        if not self._table:
            return False
        try:
            expires_at = int(time.time()) + ttl_seconds
            self._table.put_item(
                Item={
                    "idempotency_key": key,
                    "created_at": int(time.time()),
                    "expires_at": expires_at,
                    "account_id": str(payload_meta.get("account_id", "")),
                    "merchant_id": str(payload_meta.get("merchant_id", ""))
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to put idempotency key {key}: {e}")
            return False

dynamodb_client = DynamoDBClient()


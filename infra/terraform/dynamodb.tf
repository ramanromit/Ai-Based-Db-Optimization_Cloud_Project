# 1.5 DynamoDB Table (On-Demand)

resource "aws_dynamodb_table" "idempotency_keys" {
  name         = "caqi-idempotency-keys"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "idempotency_key"

  attribute {
    name = "idempotency_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "caqi-idempotency-keys"
  }
}


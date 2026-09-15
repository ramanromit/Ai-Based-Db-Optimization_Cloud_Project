from enum import Enum
from typing import Dict, Any, Optional
import uuid
import time
from pydantic import BaseModel, Field
from tagger.models import CriticalityTier

class QueryType(str, Enum):
    # Auth-Critical (P0)
    BALANCE_CHECK = "BALANCE_CHECK"
    IDEMPOTENCY_LOOKUP = "IDEMPOTENCY_LOOKUP"
    FRAUD_CHECKPOINT_READ = "FRAUD_CHECKPOINT_READ"
    TOKEN_VALIDATION = "TOKEN_VALIDATION"
    
    # Settlement-Critical (P1)
    LEDGER_ENTRY_WRITE = "LEDGER_ENTRY_WRITE"
    BATCH_SETTLEMENT_UPDATE = "BATCH_SETTLEMENT_UPDATE"
    RECONCILIATION_CHECK = "RECONCILIATION_CHECK"
    MERCHANT_PAYOUT_UPDATE = "MERCHANT_PAYOUT_UPDATE"
    
    # Analytical (P2)
    MERCHANT_DAILY_SUMMARY = "MERCHANT_DAILY_SUMMARY"
    RISK_AGGREGATION = "RISK_AGGREGATION"
    BI_VOLUME_METRICS = "BI_VOLUME_METRICS"
    AUDIT_LOG_EXPORT = "AUDIT_LOG_EXPORT"

class QueryEvent(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    service_name: str
    tier: CriticalityTier
    query_type: QueryType
    target_table: str
    latency_budget_ms: float
    simulated_workload_cost: float = Field(
        ..., description="Computational cost proxy in millicore-ms / IO tokens"
    )
    payload_meta: Dict[str, Any] = Field(default_factory=dict)

class WorkloadMixConfig(BaseModel):
    auth_ratio: float = 0.15
    settlement_ratio: float = 0.35
    analytical_ratio: float = 0.50
    base_qps: float = 100.0
    spike_multiplier: float = 5.0
    spike_duration_seconds: float = 10.0

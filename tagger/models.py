from enum import Enum
from typing import Dict
from pydantic import BaseModel, Field

class CriticalityTier(str, Enum):
    AUTH_CRITICAL = "AUTH_CRITICAL"
    SETTLEMENT_CRITICAL = "SETTLEMENT_CRITICAL"
    ANALYTICAL = "ANALYTICAL"

class TierSLAConfig(BaseModel):
    tier: CriticalityTier
    p99_budget_ms: float
    description: str
    target_availability: float = 0.999

# Default SLAs for payment architecture
DEFAULT_SLAS: Dict[CriticalityTier, TierSLAConfig] = {
    CriticalityTier.AUTH_CRITICAL: TierSLAConfig(
        tier=CriticalityTier.AUTH_CRITICAL,
        p99_budget_ms=10.0,
        description="Payment authorization hot-path: balance checks, idempotency, fraud checkpoints",
        target_availability=0.9999
    ),
    CriticalityTier.SETTLEMENT_CRITICAL: TierSLAConfig(
        tier=CriticalityTier.SETTLEMENT_CRITICAL,
        p99_budget_ms=150.0,
        description="Near-real-time settlement, clearing ledger updates, batch reconciliation",
        target_availability=0.999
    ),
    CriticalityTier.ANALYTICAL: TierSLAConfig(
        tier=CriticalityTier.ANALYTICAL,
        p99_budget_ms=1000.0,
        description="Merchant dashboards, aggregated volume metrics, BI queries, audit reporting",
        target_availability=0.99
    )
}

import random
import time
import uuid
from typing import Generator, List, Optional
from tagger.models import CriticalityTier, DEFAULT_SLAS
from tagger.tagger import tag_calling_service
from workload_gen.schemas import QueryType, QueryEvent, WorkloadMixConfig

# Service pools aligned with operational roles
AUTH_SERVICES = [
    "payment-auth-service",
    "fraud-screening-service",
    "idempotency-service",
    "token-vault"
]

SETTLEMENT_SERVICES = [
    "settlement-batch-service",
    "clearing-engine",
    "ledger-service",
    "reconciliation-worker"
]

ANALYTICAL_SERVICES = [
    "merchant-reporting-service",
    "risk-analytics-engine",
    "bi-query-service",
    "audit-exporter"
]

# Service to query types mapping
AUTH_QUERY_TYPES = [
    (QueryType.BALANCE_CHECK, "accounts", 1.0),
    (QueryType.IDEMPOTENCY_LOOKUP, "idempotency_keys", 0.8),
    (QueryType.FRAUD_CHECKPOINT_READ, "fraud_checkpoints", 1.5),
    (QueryType.TOKEN_VALIDATION, "accounts", 0.9),
]

SETTLEMENT_QUERY_TYPES = [
    (QueryType.LEDGER_ENTRY_WRITE, "transactions", 8.0),
    (QueryType.BATCH_SETTLEMENT_UPDATE, "settlement_batches", 15.0),
    (QueryType.RECONCILIATION_CHECK, "transactions", 12.0),
    (QueryType.MERCHANT_PAYOUT_UPDATE, "merchants", 10.0),
]

ANALYTICAL_QUERY_TYPES = [
    (QueryType.MERCHANT_DAILY_SUMMARY, "transactions", 45.0),
    (QueryType.RISK_AGGREGATION, "fraud_checkpoints", 65.0),
    (QueryType.BI_VOLUME_METRICS, "settlement_batches", 80.0),
    (QueryType.AUDIT_LOG_EXPORT, "transactions", 120.0),
]

class WorkloadGenerator:
    """
    Synthetic Payment Workload Generator.
    Produces mixed streams of Auth, Settlement, and Analytical queries
    with realistic distributions modeled after TPC-C payment workflows and IEEE-CIS features.
    """

    def __init__(self, config: Optional[WorkloadMixConfig] = None, seed: Optional[int] = None):
        self.config = config or WorkloadMixConfig()
        if seed is not None:
            random.seed(seed)
            
        self.is_spike_active = False
        self.spike_end_time = 0.0
        self.spike_multiplier = self.config.spike_multiplier

    def trigger_spike(self, multiplier: Optional[float] = None, duration_seconds: Optional[float] = None):
        """Triggers a high-load traffic spike (e.g. flash-sale event)."""
        mult = multiplier if multiplier is not None else self.config.spike_multiplier
        dur = duration_seconds if duration_seconds is not None else self.config.spike_duration_seconds
        self.is_spike_active = True
        self.spike_multiplier = mult
        self.spike_end_time = time.time() + dur

    def clear_spike(self):
        """Immediately resets load spike back to normal state."""
        self.is_spike_active = False
        self.spike_end_time = 0.0

    def check_spike_status(self) -> bool:
        """Returns True if a spike is currently active."""
        if self.is_spike_active:
            if time.time() > self.spike_end_time:
                self.is_spike_active = False
        return self.is_spike_active

    def _sample_ieee_cis_features(self) -> dict:
        """Simulates realistic transaction metadata following IEEE-CIS Fraud Detection dataset distributions."""
        # Log-normal distribution for transaction amount (median ~$65, right-skewed tail)
        amount = round(random.lognormvariate(3.9, 1.1), 2)
        amount = min(max(amount, 1.0), 10000.0)
        
        card4 = random.choices(["visa", "mastercard", "discover", "amex"], weights=[0.65, 0.28, 0.05, 0.02])[0]
        card6 = random.choices(["debit", "credit"], weights=[0.75, 0.25])[0]
        risk_score = round(random.betavariate(1.2, 8.0), 4) # Highly skewed towards low risk
        
        return {
            "account_id": f"acc_{random.randint(1000, 99999)}",
            "merchant_id": f"m_{random.randint(100, 5000)}",
            "transaction_amount": amount,
            "card_network": card4,
            "card_type": card6,
            "dist1": round(random.expovariate(0.05), 1),
            "fraud_risk_score": risk_score,
            "is_suspected_fraud": risk_score > 0.85,
        }

    def generate_single_query(self, forced_tier: Optional[CriticalityTier] = None) -> QueryEvent:
        """Generates a single structured query event according to mix proportions."""
        if forced_tier:
            selected_tier = forced_tier
        else:
            # Sample tier according to configured mix ratio
            selected_tier = random.choices(
                [CriticalityTier.AUTH_CRITICAL, CriticalityTier.SETTLEMENT_CRITICAL, CriticalityTier.ANALYTICAL],
                weights=[self.config.auth_ratio, self.config.settlement_ratio, self.config.analytical_ratio]
            )[0]

        now = time.time()

        if selected_tier == CriticalityTier.AUTH_CRITICAL:
            service = random.choice(AUTH_SERVICES)
            q_type, table, cost_proxy = random.choice(AUTH_QUERY_TYPES)
            sla = DEFAULT_SLAS[CriticalityTier.AUTH_CRITICAL].p99_budget_ms
            payload = self._sample_ieee_cis_features()
            payload["idempotency_key"] = str(uuid.uuid4())
            # Auth cost proxy: small variance
            cost = cost_proxy * random.uniform(0.8, 1.3)

        elif selected_tier == CriticalityTier.SETTLEMENT_CRITICAL:
            service = random.choice(SETTLEMENT_SERVICES)
            q_type, table, cost_proxy = random.choice(SETTLEMENT_QUERY_TYPES)
            sla = DEFAULT_SLAS[CriticalityTier.SETTLEMENT_CRITICAL].p99_budget_ms
            payload = {
                "batch_id": f"batch_{random.randint(100, 999)}",
                "record_count": random.randint(50, 500),
                "merchant_id": f"m_{random.randint(100, 5000)}",
            }
            cost = cost_proxy * random.uniform(0.7, 1.5)

        else: # ANALYTICAL
            service = random.choice(ANALYTICAL_SERVICES)
            q_type, table, cost_proxy = random.choice(ANALYTICAL_QUERY_TYPES)
            sla = DEFAULT_SLAS[CriticalityTier.ANALYTICAL].p99_budget_ms
            payload = {
                "aggregation_window_hours": random.choice([1, 6, 24, 72]),
                "scan_range_rows": random.randint(5000, 100000),
            }
            cost = cost_proxy * random.uniform(0.6, 2.0)

        # Structural tagging verification
        tagged_tier = tag_calling_service(service)

        return QueryEvent(
            query_id=str(uuid.uuid4()),
            timestamp=now,
            service_name=service,
            tier=tagged_tier,
            query_type=q_type,
            target_table=table,
            latency_budget_ms=sla,
            simulated_workload_cost=round(cost, 2),
            payload_meta=payload
        )

    def generate_batch(self, count: int) -> List[QueryEvent]:
        """Generates a batch of queries."""
        return [self.generate_single_query() for _ in range(count)]

    def stream_queries(self, duration_seconds: float, interval_seconds: float = 0.01) -> Generator[QueryEvent, None, None]:
        """Streams queries over time respecting intervals and load spikes."""
        start = time.time()
        while time.time() - start < duration_seconds:
            is_spike = self.check_spike_status()
            qps_mult = self.spike_multiplier if is_spike else 1.0
            
            # If in spike, yield burst queries
            batch_count = int(max(1, qps_mult))
            for _ in range(batch_count):
                yield self.generate_single_query()
                
            sleep_time = interval_seconds / qps_mult
            if sleep_time > 0:
                time.sleep(sleep_time)

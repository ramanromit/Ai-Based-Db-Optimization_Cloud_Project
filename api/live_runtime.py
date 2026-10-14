import uuid
from collections import deque
from threading import RLock
from typing import Any, Dict, Optional

import numpy as np

from evaluation.harness import load_policy
from explainability.logger import explainability_logger
from security.anomaly_detector import anomaly_detector
from storage.executor import DatabaseProxyExecutor, ExecutionResult
from tagger.models import CriticalityTier, DEFAULT_SLAS
from tagger.tagger import tag_calling_service
from workload_gen.generator import (
    ANALYTICAL_QUERY_TYPES,
    AUTH_QUERY_TYPES,
    SETTLEMENT_QUERY_TYPES,
    WorkloadGenerator,
)
from workload_gen.schemas import QueryEvent, QueryType
from workload_gen.schemas import WorkloadMixConfig


VARIANTS = ("baseline", "unconstrained", "constrained")


class LiveRuntime:
    """Shared live policy, workload, execution, and rolling-metric state."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.variant = "constrained"
        self.policy = load_policy(self.variant)
        self.generator = WorkloadGenerator()
        self.executor = DatabaseProxyExecutor()
        self.rolling_auth = [3.5]
        self.rolling_settle = [20.0]
        self.rolling_analyt = [110.0]
        self._recent_observations = deque(maxlen=100)

    def set_variant(self, variant: str) -> None:
        if variant not in VARIANTS:
            raise ValueError(f"Unsupported allocator variant: {variant}")
        with self._lock:
            self.variant = variant
            self.policy = load_policy(variant)

    def trigger_spike(self, multiplier: float, duration_seconds: float) -> None:
        with self._lock:
            self.generator.trigger_spike(multiplier, duration_seconds)

    def clear_spike(self) -> None:
        with self._lock:
            self.generator.clear_spike()

    def current_load(self) -> tuple[bool, float]:
        with self._lock:
            active = self.generator.check_spike_status()
            return active, self.generator.spike_multiplier if active else 1.0

    def _observation(self, spike_multiplier: float) -> np.ndarray:
        config = self.generator.config
        return np.array([
            config.auth_ratio * spike_multiplier,
            config.settlement_ratio * spike_multiplier,
            config.analytical_ratio * spike_multiplier,
            np.percentile(self.rolling_auth, 99) / 10.0,
            np.percentile(self.rolling_settle, 99) / 150.0,
            np.percentile(self.rolling_analyt, 99) / 1000.0,
            1.0 if spike_multiplier > 1.0 else 0.0,
            0.8 if (spike_multiplier > 1.0 and self.variant == "baseline") else 0.1,
            0.85 if self.variant == "constrained" else 0.5,
        ], dtype=np.float32)

    def decide(self, spike_multiplier: float) -> Dict[str, int]:
        with self._lock:
            observation = self._observation(spike_multiplier)
            if self.variant == "baseline":
                action, _ = self.policy.predict(observation)
            else:
                action, _ = self.policy.predict(observation, deterministic=True)
            values = [int(value) for value in action]
            return {
                "pool_priority": values[0],
                "replica_routing": values[1],
                "cache_ttl": values[2],
                "analytical_throttle": values[3],
            }

    def record_result(self, result: ExecutionResult) -> Dict[str, float]:
        with self._lock:
            if result.tier == CriticalityTier.AUTH_CRITICAL:
                values = self.rolling_auth
            elif result.tier == CriticalityTier.SETTLEMENT_CRITICAL:
                values = self.rolling_settle
            else:
                values = self.rolling_analyt
            values.append(result.latency_ms)
            if len(values) > 30:
                values.pop(0)
            return self.rolling_metrics()

    def rolling_metrics(self) -> Dict[str, float]:
        with self._lock:
            return {
                "auth_p99_ms": round(float(np.percentile(self.rolling_auth, 99)), 2),
                "settle_p99_ms": round(float(np.percentile(self.rolling_settle, 99)), 2),
                "analyt_p99_ms": round(float(np.percentile(self.rolling_analyt, 99)), 2),
            }

    def build_query(self, calling_service: str, query_type: str, target_table: Optional[str]) -> QueryEvent:
        normalized_type = query_type.strip().upper()
        aliases = {
            "BALANCE_CHECK": QueryType.BALANCE_CHECK,
            "IDEMPOTENCY_LOOKUP": QueryType.IDEMPOTENCY_LOOKUP,
            "FRAUD_CHECKPOINT": QueryType.FRAUD_CHECKPOINT_READ,
            "FRAUD_CHECKPOINT_READ": QueryType.FRAUD_CHECKPOINT_READ,
            "TOKEN_VALIDATION": QueryType.TOKEN_VALIDATION,
            "LEDGER_ENTRY": QueryType.LEDGER_ENTRY_WRITE,
            "LEDGER_ENTRY_WRITE": QueryType.LEDGER_ENTRY_WRITE,
            "BATCH_SETTLEMENT": QueryType.BATCH_SETTLEMENT_UPDATE,
            "BATCH_SETTLEMENT_UPDATE": QueryType.BATCH_SETTLEMENT_UPDATE,
            "RECONCILIATION_QUERY": QueryType.RECONCILIATION_CHECK,
            "RECONCILIATION_CHECK": QueryType.RECONCILIATION_CHECK,
            "MERCHANT_PAYOUT": QueryType.MERCHANT_PAYOUT_UPDATE,
            "MERCHANT_PAYOUT_UPDATE": QueryType.MERCHANT_PAYOUT_UPDATE,
            "MERCHANT_DAILY_SUMMARY": QueryType.MERCHANT_DAILY_SUMMARY,
            "RISK_AGGREGATION": QueryType.RISK_AGGREGATION,
            "BI_VOLUME_METRICS": QueryType.BI_VOLUME_METRICS,
            "AUDIT_LOG_EXPORT": QueryType.AUDIT_LOG_EXPORT,
        }
        if normalized_type not in aliases:
            raise ValueError(f"Unsupported query_type: {query_type}")
        selected_type = aliases[normalized_type]
        tier = tag_calling_service(calling_service)
        definitions = {
            query_type: (table, cost)
            for query_group in (AUTH_QUERY_TYPES, SETTLEMENT_QUERY_TYPES, ANALYTICAL_QUERY_TYPES)
            for query_type, table, cost in query_group
        }
        default_table, cost_proxy = definitions[selected_type]
        payload = {"source": "manual"}
        if tier == CriticalityTier.AUTH_CRITICAL:
            payload.update({"account_id": f"acc_{uuid.uuid4().hex[:8]}", "fraud_risk_score": 0.02})
        elif tier == CriticalityTier.SETTLEMENT_CRITICAL:
            payload.update({"batch_id": f"manual_{uuid.uuid4().hex[:8]}", "record_count": 1})
        else:
            payload.update({"aggregation_window_hours": 1, "scan_range_rows": 1000})
        return QueryEvent(
            service_name=calling_service,
            tier=tier,
            query_type=selected_type,
            target_table=target_table or default_table,
            latency_budget_ms=DEFAULT_SLAS[tier].p99_budget_ms,
            simulated_workload_cost=cost_proxy,
            payload_meta=payload,
        )

    def execute(self, query: QueryEvent) -> tuple[ExecutionResult, Dict[str, int], Dict[str, float], bool, float]:
        with self._lock:
            active, multiplier = self.current_load()
            action = self.decide(multiplier)

            # Parallel Security & Anomaly Check
            verdict = anomaly_detector.evaluate(query.payload_meta, query_type=query.query_type.value)
            query.risk_score = verdict.risk_score
            query.is_quarantined = verdict.is_quarantined
            query.risk_flags = verdict.flagged_reasons

            result = self.executor.execute_query(query=query, active_load_multiplier=multiplier, **{
                "action_pool_priority": action["pool_priority"],
                "action_replica_routing": action["replica_routing"],
                "action_cache_ttl": action["cache_ttl"],
                "action_analytical_throttle": action["analytical_throttle"],
            })
            self._recent_observations.append((query.tier, multiplier))
            metrics = self.record_result(result)
            return result, action, metrics, active, multiplier

    def recent_workload_config(self) -> WorkloadMixConfig:
        with self._lock:
            if not self._recent_observations:
                return self.generator.config

            counts = {tier: 0 for tier in CriticalityTier}
            multipliers = []
            for tier, multiplier in self._recent_observations:
                counts[tier] += 1
                multipliers.append(multiplier)

            total = len(self._recent_observations)
            return WorkloadMixConfig(
                auth_ratio=counts[CriticalityTier.AUTH_CRITICAL] / total,
                settlement_ratio=counts[CriticalityTier.SETTLEMENT_CRITICAL] / total,
                analytical_ratio=counts[CriticalityTier.ANALYTICAL] / total,
                spike_multiplier=sum(multipliers) / len(multipliers),
            )

    def log_result(self, action: Dict[str, int], result: ExecutionResult, multiplier: float) -> Dict[str, Any]:
        return explainability_logger.log_decision(
            variant=self.variant,
            action=action,
            auth_p99_ms=self.rolling_metrics()["auth_p99_ms"],
            sla_budget_ms=result.tier and DEFAULT_SLAS[result.tier].p99_budget_ms,
            load_multiplier=multiplier,
            queue_saturation=min(1.0, max(0.1, (multiplier - 1.0) / 5.0)),
            source="manual",
            sla_violated=result.violated_sla,
            risk_score=result.risk_score,
            security_quarantined=result.is_quarantined,
            risk_flags=result.risk_flags,
        )


live_runtime = LiveRuntime()


async def broadcast_manual_event(message: Dict[str, Any]) -> None:
    from api.websocket import manager
    await manager.broadcast(message)

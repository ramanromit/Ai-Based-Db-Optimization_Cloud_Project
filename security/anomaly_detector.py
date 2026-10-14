import time
from collections import defaultdict, deque
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

from security.models import AnomalyVerdict, ThreatTier


class AnomalyDetector:
    """
    Dual-Signal Security & Anomaly Detector for Payment Database Workloads.
    Combines:
      1. Idempotency Key Replay Detection (single-use token abuse)
      2. Rate/Velocity Anomaly Detection (burst traffic / credential stuffing)
      3. PaySim Financial Heuristics (unusual transfer amounts, balance drainage)
    """

    def __init__(
        self,
        quarantine_threshold: float = 0.65,
        suspicious_threshold: float = 0.35,
        idempotency_ttl_seconds: float = 120.0,
        rate_window_seconds: float = 10.0,
        max_rate_per_window: int = 15,
    ) -> None:
        self._lock = RLock()
        self.quarantine_threshold = quarantine_threshold
        self.suspicious_threshold = suspicious_threshold
        self.idempotency_ttl = idempotency_ttl_seconds
        self.rate_window = rate_window_seconds
        self.max_rate_per_window = max_rate_per_window

        # Cache for idempotency keys: key -> timestamp
        self._idempotency_cache: Dict[str, float] = {}
        # Velocity tracker: key -> deque of timestamps
        self._velocity_tracker: Dict[str, deque] = defaultdict(deque)

    def _clean_expired(self, now: float) -> None:
        # Purge expired idempotency keys
        expired_keys = [k for k, exp in self._idempotency_cache.items() if now - exp > self.idempotency_ttl]
        for k in expired_keys:
            del self._idempotency_cache[k]

        # Purge expired velocity entries
        for key in list(self._velocity_tracker.keys()):
            dq = self._velocity_tracker[key]
            while dq and (now - dq[0] > self.rate_window):
                dq.popleft()
            if not dq:
                del self._velocity_tracker[key]

    def evaluate(self, payload: Dict[str, Any], query_type: Optional[str] = None) -> AnomalyVerdict:
        """
        Evaluates a query event payload against idempotency, velocity, and PaySim patterns.
        """
        now = time.time()
        risk_score = 0.0
        flagged_reasons: List[str] = []

        account_id = str(payload.get("account_id", ""))
        client_ip = str(payload.get("client_ip", "10.0.0.1"))
        idempotency_key = payload.get("idempotency_key")
        force_malicious = bool(payload.get("force_malicious", False))

        with self._lock:
            self._clean_expired(now)

            # 0. Explicit demonstration / testing override
            if force_malicious:
                risk_score += 0.85
                flagged_reasons.append("MANUAL_ATTACK_SIMULATION")

            # 1. Idempotency Key Replay Detection
            if idempotency_key:
                idemp_str = str(idempotency_key)
                if idemp_str in self._idempotency_cache:
                    risk_score += 0.75
                    flagged_reasons.append("IDEMPOTENCY_REPLAY_ATTACK")
                else:
                    self._idempotency_cache[idemp_str] = now

            # 2. Velocity / Burst Anomaly Detection
            track_key = account_id if account_id else client_ip
            if track_key:
                dq = self._velocity_tracker[track_key]
                dq.append(now)
                # Purge older than window
                while dq and (now - dq[0] > self.rate_window):
                    dq.popleft()

                count = len(dq)
                if count > self.max_rate_per_window:
                    risk_score += 0.50
                    flagged_reasons.append(f"VELOCITY_BURST_{count}_REQ")
                elif count > (self.max_rate_per_window * 0.7):
                    risk_score += 0.25
                    flagged_reasons.append("HIGH_FREQUENCY_TRAFFIC")

            # 3. PaySim Financial Heuristics
            # PaySim flags: high amount transfer with drained balance or abnormal ratio
            amount = float(payload.get("amount", 0.0))
            old_balance = float(payload.get("old_balance", 0.0))
            new_balance = float(payload.get("new_balance", 0.0))
            fraud_risk_score = float(payload.get("fraud_risk_score", 0.0))

            if fraud_risk_score > 0.7:
                risk_score += 0.40
                flagged_reasons.append("ML_FRAUD_SCORE_ELEVATED")

            if amount > 50000.0:
                risk_score += 0.35
                flagged_reasons.append("PAYSIM_ANOMALOUS_HIGH_AMOUNT")

            # PaySim signature: full balance wipeout with transfer
            if old_balance > 5000.0 and new_balance == 0.0 and amount >= old_balance:
                risk_score += 0.45
                flagged_reasons.append("PAYSIM_BALANCE_DRAINAGE_PATTERN")

            # Final normalized risk clamp
            risk_score = round(min(1.0, max(0.0, risk_score)), 3)
            is_quarantined = risk_score >= self.quarantine_threshold

            if is_quarantined:
                threat_tier = ThreatTier.THREAT
            elif risk_score >= self.suspicious_threshold:
                threat_tier = ThreatTier.SUSPICIOUS
            else:
                threat_tier = ThreatTier.NORMAL

            return AnomalyVerdict(
                risk_score=risk_score,
                is_quarantined=is_quarantined,
                threat_tier=threat_tier,
                flagged_reasons=flagged_reasons,
                client_ip=client_ip,
                account_id=account_id if account_id else None,
            )


# Global singleton instance
anomaly_detector = AnomalyDetector()


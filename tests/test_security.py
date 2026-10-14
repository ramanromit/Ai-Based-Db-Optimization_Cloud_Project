import pytest
from security.anomaly_detector import AnomalyDetector
from security.models import ThreatTier


def test_clean_transaction_verdict():
    detector = AnomalyDetector()
    payload = {
        "account_id": "acc_1001",
        "client_ip": "192.168.1.10",
        "idempotency_key": "unique_key_001",
        "amount": 45.0,
        "old_balance": 1500.0,
        "new_balance": 1455.0,
        "fraud_risk_score": 0.05,
    }
    verdict = detector.evaluate(payload)
    assert verdict.risk_score < 0.35
    assert verdict.is_quarantined is False
    assert verdict.threat_tier == ThreatTier.NORMAL
    assert len(verdict.flagged_reasons) == 0


def test_idempotency_replay_quarantine():
    detector = AnomalyDetector()
    payload = {
        "account_id": "acc_1002",
        "idempotency_key": "replayed_key_999",
        "amount": 25.0,
    }
    # First execution -> clean
    v1 = detector.evaluate(payload)
    assert v1.is_quarantined is False

    # Second execution with identical key -> Replay attack flagged & quarantined
    v2 = detector.evaluate(payload)
    assert v2.risk_score >= 0.65
    assert v2.is_quarantined is True
    assert "IDEMPOTENCY_REPLAY_ATTACK" in v2.flagged_reasons
    assert v2.threat_tier == ThreatTier.THREAT


def test_paysim_drainage_pattern():
    detector = AnomalyDetector()
    payload = {
        "account_id": "acc_1003",
        "idempotency_key": "unique_key_003",
        "amount": 100000.0,
        "old_balance": 100000.0,
        "new_balance": 0.0,
        "fraud_risk_score": 0.85,
    }
    verdict = detector.evaluate(payload)
    assert verdict.is_quarantined is True
    assert "PAYSIM_BALANCE_DRAINAGE_PATTERN" in verdict.flagged_reasons
    assert "PAYSIM_ANOMALOUS_HIGH_AMOUNT" in verdict.flagged_reasons
    assert "ML_FRAUD_SCORE_ELEVATED" in verdict.flagged_reasons


def test_manual_attack_simulation():
    detector = AnomalyDetector()
    payload = {
        "account_id": "acc_manual_test",
        "force_malicious": True,
    }
    verdict = detector.evaluate(payload)
    assert verdict.risk_score >= 0.8
    assert verdict.is_quarantined is True
    assert "MANUAL_ATTACK_SIMULATION" in verdict.flagged_reasons


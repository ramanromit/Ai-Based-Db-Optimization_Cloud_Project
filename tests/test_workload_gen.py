import pytest
import time
from tagger.models import CriticalityTier
from workload_gen.schemas import WorkloadMixConfig, QueryType
from workload_gen.generator import WorkloadGenerator

def test_workload_generation_mix_proportions():
    config = WorkloadMixConfig(auth_ratio=0.2, settlement_ratio=0.3, analytical_ratio=0.5)
    gen = WorkloadGenerator(config=config, seed=42)
    
    batch = gen.generate_batch(1000)
    assert len(batch) == 1000
    
    auth_count = sum(1 for q in batch if q.tier == CriticalityTier.AUTH_CRITICAL)
    settle_count = sum(1 for q in batch if q.tier == CriticalityTier.SETTLEMENT_CRITICAL)
    analyt_count = sum(1 for q in batch if q.tier == CriticalityTier.ANALYTICAL)
    
    # Check within statistical tolerance (+/- 5%)
    assert 0.15 <= auth_count / 1000 <= 0.25
    assert 0.25 <= settle_count / 1000 <= 0.35
    assert 0.45 <= analyt_count / 1000 <= 0.55

def test_query_event_structure_and_payload():
    gen = WorkloadGenerator(seed=123)
    query = gen.generate_single_query(forced_tier=CriticalityTier.AUTH_CRITICAL)
    
    assert query.tier == CriticalityTier.AUTH_CRITICAL
    assert query.latency_budget_ms == 10.0
    assert "account_id" in query.payload_meta
    assert "fraud_risk_score" in query.payload_meta
    assert "idempotency_key" in query.payload_meta
    assert query.simulated_workload_cost > 0

def test_spike_mode_trigger_and_expiration():
    gen = WorkloadGenerator()
    assert not gen.check_spike_status()
    
    gen.trigger_spike(multiplier=4.0, duration_seconds=0.2)
    assert gen.check_spike_status()
    assert gen.spike_multiplier == 4.0
    
    time.sleep(0.25)
    assert not gen.check_spike_status()

def test_manual_spike_clear():
    gen = WorkloadGenerator()
    gen.trigger_spike(multiplier=6.0, duration_seconds=10.0)
    assert gen.check_spike_status()
    
    gen.clear_spike()
    assert not gen.check_spike_status()

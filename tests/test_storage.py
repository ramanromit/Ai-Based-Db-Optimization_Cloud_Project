import pytest
from storage.db import SessionLocal
from storage.models import Account, Merchant, FraudCheckpoint
from storage.redis_client import redis_client
from storage.executor import DatabaseProxyExecutor
from tagger.models import CriticalityTier
from workload_gen.generator import WorkloadGenerator

def test_database_seeded_data():
    session = SessionLocal()
    try:
        acc_count = session.query(Account).count()
        assert acc_count >= 1000
        merchant_count = session.query(Merchant).count()
        assert merchant_count >= 200
    finally:
        session.close()

def test_redis_operations_and_ttl():
    redis_client.set("test_key", "val_123", ex=60)
    assert redis_client.get("test_key") == "val_123"
    redis_client.delete("test_key")
    assert redis_client.get("test_key") is None

def test_executor_auth_with_priority_pool():
    executor = DatabaseProxyExecutor()
    gen = WorkloadGenerator()
    query = gen.generate_single_query(forced_tier=CriticalityTier.AUTH_CRITICAL)
    
    # Execute with high priority pool (action 2) and active spike (multiplier 4.0)
    result = executor.execute_query(
        query=query,
        action_pool_priority=2,
        action_replica_routing=1,
        action_cache_ttl=2,
        action_analytical_throttle=2,
        active_load_multiplier=4.0
    )
    
    assert result.tier == CriticalityTier.AUTH_CRITICAL
    # Auth query latency with 80% reserved pool + aggressive cache should be low (< 10ms budget)
    assert result.latency_ms < 10.0
    assert not result.violated_sla

def test_executor_auth_without_priority_under_spike():
    executor = DatabaseProxyExecutor()
    gen = WorkloadGenerator()
    query = gen.generate_single_query(forced_tier=CriticalityTier.AUTH_CRITICAL)
    
    # Execute with shared pool (action 0), no cache (action 0), under huge 8x spike
    result = executor.execute_query(
        query=query,
        action_pool_priority=0,
        action_replica_routing=0,
        action_cache_ttl=0,
        action_analytical_throttle=0,
        active_load_multiplier=8.0
    )
    
    # Contention delay in shared pool under 8x spike causes queuing delay
    assert result.queued_delay_ms > 5.0


import time
import random
import numpy as np
from typing import Dict, Any, Tuple
from tagger.models import CriticalityTier
from workload_gen.schemas import QueryEvent, QueryType
from storage.redis_client import redis_client

class ExecutionResult:
    def __init__(
        self,
        query_id: str,
        tier: CriticalityTier,
        latency_ms: float,
        is_cache_hit: bool,
        target_route: str,
        queued_delay_ms: float,
        violated_sla: bool
    ):
        self.query_id = query_id
        self.tier = tier
        self.latency_ms = latency_ms
        self.is_cache_hit = is_cache_hit
        self.target_route = target_route
        self.queued_delay_ms = queued_delay_ms
        self.violated_sla = violated_sla

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id": self.query_id,
            "tier": self.tier.value,
            "latency_ms": round(self.latency_ms, 2),
            "is_cache_hit": self.is_cache_hit,
            "target_route": self.target_route,
            "queued_delay_ms": round(self.queued_delay_ms, 2),
            "violated_sla": self.violated_sla
        }

class DatabaseProxyExecutor:
    """
    Simulates RDS Proxy and Aurora Cluster execution dynamics under
    varying connection pool allocations, replica routing, cache TTLs, and concurrency loads.
    """
    def __init__(self):
        self.redis = redis_client
        self.current_concurrency = 1.0

    def execute_query(
        self,
        query: QueryEvent,
        action_pool_priority: int,      # 0: shared, 1: 50% reserved, 2: 80% reserved
        action_replica_routing: int,     # 0: round-robin, 1: analytical-to-replica, 2: primary-only
        action_cache_ttl: int,           # 0: bypass (0s), 1: standard (60s), 2: aggressive (300s)
        action_analytical_throttle: int, # 0: none, 1: 25% delay, 2: 75% delay
        active_load_multiplier: float = 1.0
    ) -> ExecutionResult:
        """
        Executes a query through the simulated proxy given the policy actions.
        Returns execution latency, routing target, and SLA violation status.
        """
        tier = query.tier
        is_cache_hit = False
        target_route = "PRIMARY"
        queued_delay = 0.0

        # 1. Cache Layer Check (for Auth-Critical lookups e.g. Balance, Idempotency, Fraud check)
        if tier == CriticalityTier.AUTH_CRITICAL and action_cache_ttl > 0:
            cache_key = f"cache:{query.query_type.value}:{query.payload_meta.get('account_id', 'default')}"
            cached_val = self.redis.get(cache_key)
            
            # Simulated cache hit probability tied to TTL action
            hit_prob = 0.45 if action_cache_ttl == 1 else 0.85
            if cached_val or (random.random() < hit_prob):
                is_cache_hit = True
                # Redis hit latency: 0.4ms - 1.2ms
                latency_ms = random.uniform(0.4, 1.2)
                # Store back in cache with TTL
                ttl_seconds = 60 if action_cache_ttl == 1 else 300
                self.redis.set(cache_key, "1", ex=ttl_seconds)
                violated = latency_ms > query.latency_budget_ms
                return ExecutionResult(
                    query_id=query.query_id,
                    tier=tier,
                    latency_ms=latency_ms,
                    is_cache_hit=True,
                    target_route="REDIS_ELASTICACHE",
                    queued_delay_ms=0.0,
                    violated_sla=violated
                )

        # 2. Replica Routing
        if tier == CriticalityTier.ANALYTICAL:
            if action_replica_routing in [0, 1]:
                target_route = "READ_REPLICA_1" if random.random() < 0.5 else "READ_REPLICA_2"
            else:
                target_route = "PRIMARY"
        elif tier == CriticalityTier.SETTLEMENT_CRITICAL:
            # Settlement writes must go to primary
            target_route = "PRIMARY"
        else: # AUTH_CRITICAL cache miss
            target_route = "PRIMARY" if action_replica_routing != 0 else ("READ_REPLICA_1" if random.random() < 0.3 else "PRIMARY")

        # 3. Contention & Connection Pool Queueing Dynamics
        # Base execution times
        if tier == CriticalityTier.AUTH_CRITICAL:
            base_exec = random.uniform(2.0, 4.5)
        elif tier == CriticalityTier.SETTLEMENT_CRITICAL:
            base_exec = random.uniform(10.0, 28.0)
        else: # ANALYTICAL
            base_exec = random.uniform(60.0, 220.0)

        # Contention calculation based on active load spike
        effective_load = active_load_multiplier
        
        # Analytical throttling reduces background CPU contention on Primary
        if tier == CriticalityTier.ANALYTICAL:
            throttle_penalty = [0.0, 30.0, 120.0][action_analytical_throttle]
            base_exec += throttle_penalty

        if effective_load > 1.0:
            # Load spike active!
            contention_factor = (effective_load - 1.0) ** 1.3

            if tier == CriticalityTier.AUTH_CRITICAL:
                # If dedicated priority pool is active (action 1 or 2), auth queries bypass contention
                if action_pool_priority == 2:
                    # 80% reserved high-priority pool: practically zero queuing
                    queued_delay = random.uniform(0.1, 0.8)
                elif action_pool_priority == 1:
                    # 50% reserved pool: minor queueing
                    queued_delay = random.uniform(0.5, 2.5) * contention_factor
                else:
                    # 0: shared pool! Auth queries get stuck behind heavy analytical queries!
                    queued_delay = random.uniform(8.0, 25.0) * contention_factor
            
            elif tier == CriticalityTier.SETTLEMENT_CRITICAL:
                queued_delay = random.uniform(4.0, 15.0) * contention_factor
            else: # ANALYTICAL
                queued_delay = random.uniform(25.0, 90.0) * contention_factor

        total_latency = base_exec + queued_delay
        violated = total_latency > query.latency_budget_ms

        return ExecutionResult(
            query_id=query.query_id,
            tier=tier,
            latency_ms=total_latency,
            is_cache_hit=False,
            target_route=target_route,
            queued_delay_ms=queued_delay,
            violated_sla=violated
        )


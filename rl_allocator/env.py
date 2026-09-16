import gymnasium as gym
from gymnasium import spaces
import numpy as np
import time
from typing import Dict, Any, Tuple, Optional

from tagger.models import CriticalityTier
from workload_gen.generator import WorkloadGenerator
from workload_gen.schemas import WorkloadMixConfig
from storage.executor import DatabaseProxyExecutor

class PaymentCMDPEnv(gym.Env):
    """
    Constrained Markov Decision Process (CMDP) Environment for Autonomous Database Query Optimization.
    Simulates payment database proxy dynamics under varying load patterns and spikes.
    
    Constraint: P(auth_critical_p99 <= 10.0ms) >= 1 - delta
    Lagrangian relaxation dynamically penalizes policy when Auth SLA is violated.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        use_constraint: bool = True,
        auth_sla_budget_ms: float = 10.0,
        initial_lambda: float = 2.0,
        lambda_lr: float = 0.05,
        step_query_count: int = 50,
        spike_probability: float = 0.15,
        seed: Optional[int] = None
    ):
        super().__init__()
        
        self.use_constraint = use_constraint
        self.auth_sla_budget_ms = auth_sla_budget_ms
        self.lagrangian_lambda = initial_lambda if use_constraint else 0.0
        self.lambda_lr = lambda_lr
        self.step_query_count = step_query_count
        self.spike_probability = spike_probability
        
        # Generator & Executor
        self.workload_config = WorkloadMixConfig()
        self.generator = WorkloadGenerator(config=self.workload_config, seed=seed)
        self.executor = DatabaseProxyExecutor()
        
        # State: 9 continuous metrics:
        # [auth_qps_norm, settle_qps_norm, analyt_qps_norm,
        #  auth_p99_norm, settle_p99_norm, analyt_p99_norm,
        #  spike_active_flag, queue_saturation_proxy, cache_hit_ratio]
        self.observation_space = spaces.Box(
            low=0.0,
            high=10.0,
            shape=(9,),
            dtype=np.float32
        )
        
        # Action space: MultiDiscrete([3, 3, 3, 3])
        # 0: pool_priority (0: shared, 1: 50% reserved, 2: 80% reserved)
        # 1: replica_routing (0: round-robin, 1: analyt-to-replica, 2: primary-only)
        # 2: cache_ttl (0: bypass, 1: 60s, 2: 300s)
        # 3: analytical_throttle (0: none, 1: 25% delay, 2: 75% delay)
        self.action_space = spaces.MultiDiscrete([3, 3, 3, 3])
        
        self.current_step = 0
        self.max_steps = 200
        
        # State tracking
        self.history_auth_p99 = 4.0
        self.history_settle_p99 = 20.0
        self.history_analyt_p99 = 120.0
        self.current_spike_factor = 1.0
        self.last_cache_hit_ratio = 0.5
        self.last_queue_saturation = 0.1

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self.generator = WorkloadGenerator(config=self.workload_config, seed=seed)
            
        self.current_step = 0
        self.generator.clear_spike()
        self.current_spike_factor = 1.0
        self.history_auth_p99 = 4.0
        self.history_settle_p99 = 20.0
        self.history_analyt_p99 = 120.0
        self.last_cache_hit_ratio = 0.5
        self.last_queue_saturation = 0.1
        
        obs = self._get_obs()
        return obs, {}

    def _get_obs(self) -> np.ndarray:
        # Normalized observation vector
        auth_norm = self.workload_config.auth_ratio * self.current_spike_factor
        settle_norm = self.workload_config.settlement_ratio * self.current_spike_factor
        analyt_norm = self.workload_config.analytical_ratio * self.current_spike_factor
        
        auth_p99_norm = self.history_auth_p99 / self.auth_sla_budget_ms
        settle_p99_norm = self.history_settle_p99 / 150.0
        analyt_p99_norm = self.history_analyt_p99 / 1000.0
        
        spike_flag = 1.0 if self.current_spike_factor > 1.0 else 0.0
        
        return np.array([
            auth_norm,
            settle_norm,
            analyt_norm,
            auth_p99_norm,
            settle_p99_norm,
            analyt_p99_norm,
            spike_flag,
            self.last_queue_saturation,
            self.last_cache_hit_ratio
        ], dtype=np.float32)

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.current_step += 1
        
        pool_prio, replica_route, cache_ttl, analyt_throttle = action
        
        # Stochastically introduce or clear load spike
        if np.random.rand() < self.spike_probability and self.current_spike_factor == 1.0:
            self.current_spike_factor = np.random.uniform(3.5, 6.0)
            self.generator.trigger_spike(multiplier=self.current_spike_factor, duration_seconds=5.0)
        elif self.current_spike_factor > 1.0 and np.random.rand() < 0.25:
            self.current_spike_factor = 1.0
            self.generator.clear_spike()

        # Generate a batch of queries for this step
        queries = self.generator.generate_batch(self.step_query_count)
        
        auth_latencies = []
        settle_latencies = []
        analyt_latencies = []
        cache_hits = 0
        total_auth = 0
        
        for q in queries:
            res = self.executor.execute_query(
                query=q,
                action_pool_priority=int(pool_prio),
                action_replica_routing=int(replica_route),
                action_cache_ttl=int(cache_ttl),
                action_analytical_throttle=int(analyt_throttle),
                active_load_multiplier=self.current_spike_factor
            )
            
            if q.tier == CriticalityTier.AUTH_CRITICAL:
                auth_latencies.append(res.latency_ms)
                total_auth += 1
                if res.is_cache_hit:
                    cache_hits += 1
            elif q.tier == CriticalityTier.SETTLEMENT_CRITICAL:
                settle_latencies.append(res.latency_ms)
            else:
                analyt_latencies.append(res.latency_ms)

        # Compute percentile metrics
        auth_p99 = float(np.percentile(auth_latencies, 99)) if auth_latencies else 3.0
        settle_p99 = float(np.percentile(settle_latencies, 99)) if settle_latencies else 20.0
        analyt_p99 = float(np.percentile(analyt_latencies, 99)) if analyt_latencies else 100.0
        
        self.history_auth_p99 = auth_p99
        self.history_settle_p99 = settle_p99
        self.history_analyt_p99 = analyt_p99
        self.last_cache_hit_ratio = (cache_hits / total_auth) if total_auth > 0 else 0.5
        self.last_queue_saturation = min(1.0, (self.current_spike_factor - 1.0) / 4.0 if pool_prio == 0 else 0.1)

        # --- REWARD CALCULATION ---
        # 1. Base Throughput & Latency Satisfaction Term
        # Normalizes latency satisfaction: lower is better
        auth_satisfaction = max(0.0, 1.0 - (auth_p99 / (self.auth_sla_budget_ms * 2.0)))
        settle_satisfaction = max(0.0, 1.0 - (settle_p99 / 300.0))
        analyt_satisfaction = max(0.0, 1.0 - (analyt_p99 / 2000.0))
        
        # Overall performance reward (weighted towards auth and settlement)
        throughput_term = 0.5 * auth_satisfaction + 0.3 * settle_satisfaction + 0.2 * analyt_satisfaction
        
        # 2. Resource & Degradation Cost Term
        # Aggressive caching + dedicated pool reservation + heavy throttling incur a small infrastructure/cost overhead
        cost_term = 0.05 * (pool_prio / 2.0) + 0.04 * (cache_ttl / 2.0) + 0.06 * (analyt_throttle / 2.0)
        
        base_reward = throughput_term - cost_term
        
        # 3. Lagrangian Constraint Term: Hard SLA protection for Auth-Critical
        constraint_violation = max(0.0, auth_p99 - self.auth_sla_budget_ms)
        normalized_violation = constraint_violation / self.auth_sla_budget_ms
        
        constraint_penalty = 0.0
        if self.use_constraint:
            constraint_penalty = self.lagrangian_lambda * normalized_violation
            # Dual update: lambda <- max(0.1, min(50.0, lambda + lr * violation))
            self.lagrangian_lambda = float(np.clip(
                self.lagrangian_lambda + self.lambda_lr * (normalized_violation - 0.01),
                0.1,
                50.0
            ))
            
        reward = base_reward - constraint_penalty
        
        terminated = False
        truncated = self.current_step >= self.max_steps
        
        info = {
            "step": self.current_step,
            "auth_p99_ms": auth_p99,
            "settle_p99_ms": settle_p99,
            "analyt_p99_ms": analyt_p99,
            "violated_auth_sla": auth_p99 > self.auth_sla_budget_ms,
            "lagrangian_lambda": self.lagrangian_lambda,
            "spike_factor": self.current_spike_factor,
            "cache_hit_ratio": self.last_cache_hit_ratio,
            "throughput_reward": throughput_term,
            "constraint_penalty": constraint_penalty
        }
        
        obs = self._get_obs()
        return obs, float(reward), terminated, truncated, info


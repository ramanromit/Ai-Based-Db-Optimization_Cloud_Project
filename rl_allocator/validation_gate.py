import os
import numpy as np
from typing import Tuple, Dict, Any
from stable_baselines3 import PPO

from rl_allocator.env import PaymentCMDPEnv
from workload_gen.schemas import WorkloadMixConfig

def evaluate_policy(model_path: str, workload_config: WorkloadMixConfig, num_episodes: int = 5) -> Dict[str, Any]:
    """Runs a policy in the environment and aggregates metrics."""
    env = PaymentCMDPEnv(
        use_constraint=True,
        step_query_count=50,
        spike_probability=0.20,
        workload_config=workload_config,
        seed=42 # fixed seed for fair comparison
    )
    
    try:
        model = PPO.load(model_path)
    except Exception as e:
        print(f"Failed to load model {model_path}: {e}")
        return {"auth_p99_ms": 999.0, "violation_rate": 1.0, "throughput_reward": -999.0}

    all_auth_p99 = []
    violations = 0
    total_steps = 0
    rewards = []
    
    for _ in range(num_episodes):
        obs, _ = env.reset()
        done = False
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            
            all_auth_p99.append(info.get("auth_p99_ms", 10.0))
            if info.get("violated_auth_sla", False):
                violations += 1
            rewards.append(reward)
            total_steps += 1
            
    avg_p99 = float(np.mean(all_auth_p99))
    violation_rate = float(violations) / max(1, total_steps)
    avg_reward = float(np.mean(rewards))
    
    return {
        "auth_p99_ms": avg_p99,
        "violation_rate": violation_rate,
        "compliance_pct": max(0.0, 100.0 * (1.0 - violation_rate)),
        "throughput_reward": avg_reward
    }

def validate_new_policy(candidate_path: str, live_path: str, workload_config: WorkloadMixConfig) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
    """
    Evaluates the candidate policy against the live policy.
    Returns (is_approved, candidate_metrics, live_metrics).
    """
    candidate_metrics = evaluate_policy(candidate_path, workload_config)
    live_metrics = evaluate_policy(live_path, workload_config)
    
    # Validation Rules
    # 1. Candidate must not have catastrophic SLA violation (e.g., >5% worse than live, or absolute > 5%)
    # 2. Candidate average P99 must be <= 10.0ms (SLA)
    
    candidate_compliance = candidate_metrics["compliance_pct"]
    live_compliance = live_metrics["compliance_pct"]
    
    is_safe_p99 = candidate_metrics["auth_p99_ms"] <= 10.0
    
    # We tolerate a tiny degradation in compliance if it's still near 100%, 
    # but strictly block if it's notably worse.
    is_better_or_equal = candidate_compliance >= (live_compliance - 1.0)
    
    is_approved = is_safe_p99 and is_better_or_equal
    
    return is_approved, candidate_metrics, live_metrics

import os
import random
import time
from typing import Dict, Any

from stable_baselines3 import PPO
from rl_allocator.env import PaymentCMDPEnv
from rl_allocator.train import ConstraintLoggingCallback
from workload_gen.schemas import WorkloadMixConfig
from explainability.logger import explainability_logger

def get_recent_workload_config() -> WorkloadMixConfig:
    """
    Computes a WorkloadMixConfig that reflects recently observed traffic patterns.
    In a real system, this would query Prometheus/Datadog for the last N hours of traffic ratios.
    Here, we extract recent metrics from the ExplainabilityLogger and apply a realistic drift,
    ensuring the RL agent trains on an evolving snapshot, not a static config.
    """
    # Fetch recent logs to understand recent load multipliers
    recent_logs = explainability_logger.get_recent_logs(limit=100)
    
    # Calculate average recent spike multiplier
    avg_multiplier = 1.0
    if recent_logs:
        multipliers = [log.get("load_multiplier", 1.0) for log in recent_logs]
        avg_multiplier = sum(multipliers) / len(multipliers)
    
    # Simulate workload drift by perturbing the base ratios
    # e.g., if there's been high load, maybe analytical queries are backed up, so they increase in the mix.
    base_auth = 0.60
    base_settle = 0.30
    base_analyt = 0.10
    
    drift = random.uniform(-0.1, 0.1)
    
    new_auth = max(0.2, base_auth + drift)
    new_settle = max(0.1, base_settle - (drift / 2))
    new_analyt = max(0.05, base_analyt - (drift / 2))
    
    # Normalize
    total = new_auth + new_settle + new_analyt
    return WorkloadMixConfig(
        auth_ratio=new_auth / total,
        settlement_ratio=new_settle / total,
        analytical_ratio=new_analyt / total,
        spike_multiplier=max(1.0, min(10.0, avg_multiplier * random.uniform(0.9, 1.2)))
    )

def run_retrain_job(trigger_reason: str, force_bad: bool = False, output_dir: str = "rl_allocator/checkpoints") -> str:
    """
    Executes a retraining job using a dynamic workload snapshot.
    Returns the path to the candidate checkpoint.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Fetch dynamic workload snapshot
    workload_config = get_recent_workload_config()
    print(f"[Retrain] Snapshot Ratios - Auth: {workload_config.auth_ratio:.2f}, Settle: {workload_config.settlement_ratio:.2f}, Analyt: {workload_config.analytical_ratio:.2f}")
    
    # 2. Configure Environment
    env = PaymentCMDPEnv(
        use_constraint=True,
        step_query_count=50,
        spike_probability=0.25 if force_bad else 0.15,
        workload_config=workload_config
    )
    
    model = PPO(
        policy="MlpPolicy",
        env=env,
        learning_rate=0.0003 if not force_bad else 0.05, # high learning rate to corrupt bad model
        n_steps=128,
        batch_size=64,
        verbose=0
    )
    
    # 3. Train
    # If force_bad is True, we only train for 128 timesteps (extremely undertrained, bad policy).
    # Otherwise, train for 2048 timesteps to produce a decent candidate.
    total_timesteps = 128 if force_bad else 2048
    
    model.learn(total_timesteps=total_timesteps)
    
    version_tag = f"v{int(time.time())}"
    if force_bad:
        version_tag += "_bad"
        
    checkpoint_filename = f"candidate_constrained_{version_tag}.zip"
    checkpoint_path = os.path.join(output_dir, checkpoint_filename)
    
    model.save(checkpoint_path)
    print(f"[Retrain] Candidate saved to {checkpoint_path}")
    
    return checkpoint_path

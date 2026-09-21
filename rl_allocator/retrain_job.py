import os
import time
from typing import Dict, Any

from stable_baselines3 import PPO
from rl_allocator.env import PaymentCMDPEnv
from rl_allocator.train import ConstraintLoggingCallback
from workload_gen.schemas import WorkloadMixConfig
from api.live_runtime import live_runtime

def get_recent_workload_config() -> WorkloadMixConfig:
    """
    Computes a WorkloadMixConfig from the most recent live query observations.
    Retraining is refused when no observed traffic is available instead of silently
    training against a static or fabricated workload mix.
    """
    return live_runtime.recent_workload_config()

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

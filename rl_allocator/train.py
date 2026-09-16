import os
import argparse
import yaml
import torch
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from rl_allocator.env import PaymentCMDPEnv

class ConstraintLoggingCallback(BaseCallback):
    """Logs SLA violations and Lagrangian multiplier trajectory during training."""
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.step_counter = 0

    def _on_step(self) -> bool:
        self.step_counter += 1
        if self.step_counter % 2000 == 0:
            infos = self.locals.get("infos", [])
            if infos:
                last_info = infos[0]
                auth_p99 = last_info.get("auth_p99_ms", 0.0)
                violated = last_info.get("violated_auth_sla", False)
                lam = last_info.get("lagrangian_lambda", 0.0)
                print(f"[Train Step {self.step_counter}] Auth P99: {auth_p99:.2f}ms | Violated: {violated} | Lambda: {lam:.2f}")
        return True

def train_agent(config_path: str, seed: int = 42, output_dir: str = "rl_allocator/checkpoints"):
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)

    variant_name = "constrained" if cfg.get("use_constraint", True) else "unconstrained"
    os.makedirs(output_dir, exist_ok=True)
    
    # Set reproducibility seeds
    torch.manual_seed(seed)
    np.random.seed(seed)

    print(f"\n=======================================================")
    print(f"Starting Training: Variant={variant_name} | Seed={seed}")
    print(f"Constraint Enforcement: {cfg.get('use_constraint', True)}")
    print(f"=======================================================")

    env = PaymentCMDPEnv(
        use_constraint=cfg.get("use_constraint", True),
        auth_sla_budget_ms=cfg.get("auth_sla_budget_ms", 10.0),
        initial_lambda=cfg.get("initial_lambda", 2.0),
        lambda_lr=cfg.get("lambda_lr", 0.05),
        step_query_count=cfg.get("step_query_count", 50),
        spike_probability=cfg.get("spike_probability", 0.20),
        seed=seed
    )

    model = PPO(
        policy=cfg.get("policy", "MlpPolicy"),
        env=env,
        learning_rate=cfg.get("learning_rate", 0.0003),
        n_steps=cfg.get("n_steps", 128),
        batch_size=cfg.get("batch_size", 64),
        n_epochs=cfg.get("n_epochs", 10),
        gamma=cfg.get("gamma", 0.99),
        gae_lambda=cfg.get("gae_lambda", 0.95),
        clip_range=cfg.get("clip_range", 0.2),
        ent_coef=cfg.get("ent_coef", 0.01),
        verbose=0,
        seed=seed
    )

    total_timesteps = cfg.get("total_timesteps", 15000)
    callback = ConstraintLoggingCallback()
    
    model.learn(total_timesteps=total_timesteps, callback=callback)

    checkpoint_filename = f"{variant_name}_seed_{seed}.zip"
    checkpoint_path = os.path.join(output_dir, checkpoint_filename)
    model.save(checkpoint_path)
    print(f"Successfully saved checkpoint: {checkpoint_path}\n")

    return model, checkpoint_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CAQI RL Agent")
    parser.add_argument("--config", type=str, default="rl_allocator/configs/constrained.yaml", help="Path to YAML config")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, default="rl_allocator/checkpoints", help="Directory to save model checkpoints")
    
    args = parser.parse_args()
    train_agent(config_path=args.config, seed=args.seed, output_dir=args.output_dir)


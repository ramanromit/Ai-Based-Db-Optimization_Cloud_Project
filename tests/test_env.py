import pytest
import numpy as np
from rl_allocator.env import PaymentCMDPEnv

def test_cmdp_env_initialization():
    env = PaymentCMDPEnv(use_constraint=True, auth_sla_budget_ms=10.0, initial_lambda=2.0)
    obs, info = env.reset(seed=42)
    
    assert obs.shape == (9,)
    assert np.all(obs >= 0.0)
    assert env.action_space.shape == (4,)

def test_cmdp_env_step_execution():
    env = PaymentCMDPEnv(use_constraint=True, step_query_count=20)
    obs, _ = env.reset(seed=42)
    
    action = np.array([2, 1, 2, 1]) # [80% prio, analyt-to-replica, aggressive cache, 25% throttle]
    next_obs, reward, terminated, truncated, info = env.step(action)
    
    assert next_obs.shape == (9,)
    assert isinstance(reward, float)
    assert not terminated
    assert "auth_p99_ms" in info
    assert "violated_auth_sla" in info
    assert "lagrangian_lambda" in info

def test_unconstrained_env_zero_penalty():
    env = PaymentCMDPEnv(use_constraint=False, step_query_count=20)
    obs, _ = env.reset(seed=42)
    
    action = np.array([0, 0, 0, 0]) # shared pool, round-robin, no cache
    _, _, _, _, info = env.step(action)
    
    assert info["constraint_penalty"] == 0.0
    assert info["lagrangian_lambda"] == 0.0


import numpy as np
from typing import Dict, Any, Optional

class StaticBaselineAllocator:
    """
    Criticality-Agnostic Baseline Allocator.
    Emulates default cloud database proxy behavior (e.g. AWS Aurora Auto-Scaling / standard RDS Proxy):
    - Shared FIFO connection pool (no priority reservation)
    - Uniform round-robin replica distribution
    - Static default cache TTL (60s)
    - Zero query throttling on analytical batches
    """
    def __init__(self, name: str = "CriticalityAgnosticBaseline"):
        self.name = name

    def predict(self, observation: np.ndarray, deterministic: bool = True) -> np.ndarray:
        """
        Returns fixed action:
        - pool_priority = 0 (Shared connection pool, no reservation)
        - replica_routing = 0 (Uniform round-robin)
        - cache_ttl = 1 (Static default TTL 60s)
        - analytical_throttle = 0 (No throttling of background queries)
        """
        action = np.array([0, 0, 1, 0], dtype=np.int64)
        return action, None

    def select_action(self, observation: np.ndarray) -> np.ndarray:
        action, _ = self.predict(observation)
        return action


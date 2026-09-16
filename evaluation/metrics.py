import numpy as np
from typing import List, Dict, Any

def compute_percentiles(latencies: List[float]) -> Dict[str, float]:
    """Computes p50, p90, p95, and p99 from a list of latency samples."""
    if not latencies:
        return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}
    arr = np.array(latencies)
    return {
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
    }

def compute_sla_compliance(latencies: List[float], budget_ms: float = 10.0) -> float:
    """Returns the proportion of requests that met the SLA budget (0.0 to 1.0)."""
    if not latencies:
        return 1.0
    arr = np.array(latencies)
    compliant = np.sum(arr <= budget_ms)
    return float(compliant / len(arr))

def summarize_evaluation_run(
    variant: str,
    seed: int,
    auth_latencies: List[float],
    settle_latencies: List[float],
    analyt_latencies: List[float],
    total_queries: int,
    elapsed_seconds: float,
    resource_cost_samples: List[float],
    auth_budget_ms: float = 10.0
) -> Dict[str, Any]:
    """Computes standardized benchmark metrics for a single variant evaluation run."""
    auth_p = compute_percentiles(auth_latencies)
    settle_p = compute_percentiles(settle_latencies)
    analyt_p = compute_percentiles(analyt_latencies)
    
    compliance = compute_sla_compliance(auth_latencies, budget_ms=auth_budget_ms)
    violations = sum(1 for l in auth_latencies if l > auth_budget_ms)
    throughput = total_queries / max(elapsed_seconds, 0.001)
    cost = float(np.mean(resource_cost_samples)) if resource_cost_samples else 1.0

    return {
        "variant": variant,
        "seed": seed,
        "auth_p50_ms": round(auth_p["p50"], 2),
        "auth_p95_ms": round(auth_p["p95"], 2),
        "auth_p99_ms": round(auth_p["p99"], 2),
        "auth_sla_compliance_pct": round(compliance * 100.0, 2),
        "auth_violations_count": violations,
        "settle_p99_ms": round(settle_p["p99"], 2),
        "analyt_p99_ms": round(analyt_p["p99"], 2),
        "throughput_qps": round(throughput, 2),
        "avg_resource_cost": round(cost, 3),
        "total_queries": total_queries
    }


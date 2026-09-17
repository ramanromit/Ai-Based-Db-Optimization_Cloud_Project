import os
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from tagger.models import CriticalityTier, DEFAULT_SLAS
from explainability.logger import explainability_logger
from evaluation.harness import run_evaluation_scenario, load_policy
from workload_gen.generator import WorkloadGenerator

router = APIRouter(prefix="/api")
router = APIRouter()

# Shared singleton generator for interactive API operations
interactive_generator = WorkloadGenerator()

class SpikeRequest(BaseModel):
    multiplier: float = Field(default=5.0, ge=1.0, le=20.0, description="Traffic burst multiplier")
    duration_seconds: float = Field(default=15.0, ge=1.0, le=300.0, description="Spike duration in seconds")

class CompareRequest(BaseModel):
    queries_per_variant: int = Field(default=300, ge=50, le=2000)
    spike_multiplier: float = Field(default=5.0, ge=1.0, le=10.0)

@router.get("/health")
def get_health() -> Dict[str, Any]:
    constrained_ckpt = os.path.exists("rl_allocator/checkpoints/constrained_seed_42.zip")
    unconstrained_ckpt = os.path.exists("rl_allocator/checkpoints/unconstrained_seed_42.zip")
    
    return {
        "status": "HEALTHY",
        "timestamp": time.time(),
        "models": {
            "constrained_agent_ready": constrained_ckpt,
            "unconstrained_agent_ready": unconstrained_ckpt,
            "baseline_agent_ready": True
        },
        "slas": {
            tier.value: sla.p99_budget_ms for tier, sla in DEFAULT_SLAS.items()
        },
        "spike_active": interactive_generator.check_spike_status()
    }

@router.get("/metrics")
def get_tier_metrics() -> Dict[str, Any]:
    """Returns current latency metrics, SLA compliance stats, and budgets per tier."""
    summary_path = "evaluation/evaluation_summary.csv"
    latest_bench = []
    if os.path.exists(summary_path):
        try:
            df = pd.read_csv(summary_path)
            latest_bench = df.to_dict(orient="records")
        except Exception:
            pass

    return {
        "timestamp": time.time(),
        "spike_active": interactive_generator.check_spike_status(),
        "slas": {
            "AUTH_CRITICAL": {"budget_ms": 10.0, "description": "Payment auth hot path"},
            "SETTLEMENT_CRITICAL": {"budget_ms": 150.0, "description": "Ledger & clearing"},
            "ANALYTICAL": {"budget_ms": 1000.0, "description": "BI & reporting"}
        },
        "benchmark_summary": latest_bench
    }

@router.post("/trigger-spike")
def trigger_spike(req: SpikeRequest) -> Dict[str, Any]:
    interactive_generator.trigger_spike(multiplier=req.multiplier, duration_seconds=req.duration_seconds)
def trigger_spike(req: Optional[SpikeRequest] = None) -> Dict[str, Any]:
    multiplier = req.multiplier if req else 5.0
    duration_seconds = req.duration_seconds if req else 15.0
    interactive_generator.trigger_spike(multiplier=multiplier, duration_seconds=duration_seconds)
    return {
        "status": "SPIKE_TRIGGERED",
        "multiplier": req.multiplier,
        "duration_seconds": req.duration_seconds,
        "multiplier": multiplier,
        "duration_seconds": duration_seconds,
        "end_time": interactive_generator.spike_end_time
    }

@router.post("/clear-spike")
def clear_spike() -> Dict[str, Any]:
    interactive_generator.clear_spike()
    return {"status": "SPIKE_CLEARED"}

@router.get("/explainability")
def get_explainability_feed(limit: int = Query(default=30, ge=1, le=200)) -> List[Dict[str, Any]]:
    return explainability_logger.get_recent_logs(limit=limit)

@router.get("/ablation-summary")
def get_ablation_summary() -> List[Dict[str, Any]]:
    summary_path = "evaluation/evaluation_summary.csv"
    if not os.path.exists(summary_path):
        raise HTTPException(status_code=404, detail="Ablation summary not yet generated. Run evaluation harness.")
    df = pd.read_csv(summary_path)
    return df.to_dict(orient="records")

@router.get("/compare")
def compare_get(
    variant: Optional[str] = Query(default=None),
    queries: int = Query(default=300),
    spike_mult: float = Query(default=5.0)
) -> Dict[str, Any]:
    return run_compare(queries_count=queries, multiplier=spike_mult, selected_variant=variant)

@router.post("/compare")
def compare_variants_on_demand(req: CompareRequest) -> Dict[str, Any]:
    """Runs a quick live comparative evaluation of Baseline vs Unconstrained vs Constrained."""
def compare_post(req: CompareRequest) -> Dict[str, Any]:
    return run_compare(queries_count=req.queries_per_variant, multiplier=req.spike_multiplier, selected_variant=None)

def run_compare(queries_count: int, multiplier: float, selected_variant: Optional[str]) -> Dict[str, Any]:
    selected_variants = [selected_variant] if selected_variant in ["baseline", "unconstrained", "constrained"] else ["baseline", "unconstrained", "constrained"]
    results = {}
    variants = ["baseline", "unconstrained", "constrained"]
    
    for var in variants:
    for v in selected_variants:
        try:
            policy = load_policy(var, seed=42)
            policy = load_policy(v, seed=42)
            summary = run_evaluation_scenario(
                variant=var,
                variant=v,
                policy=policy,
                total_queries=req.queries_per_variant,
                spike_multiplier=req.spike_multiplier,
                total_queries=queries_count,
                spike_multiplier=multiplier,
                seed=42
            )
            results[var] = summary
            results[v] = summary
        except Exception as e:
            results[var] = {"error": str(e)}
            results[v] = {"error": str(e)}
            
    return {
        "status": "COMPLETED",
        "queries_per_variant": req.queries_per_variant,
        "spike_multiplier": req.spike_multiplier,
        "queries_per_variant": queries_count,
        "spike_multiplier": multiplier,
        "results": results
    }


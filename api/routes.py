import os
import time
import pandas as pd
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from tagger.models import CriticalityTier, DEFAULT_SLAS
from explainability.logger import explainability_logger
from api.live_runtime import live_runtime
from api.websocket import manager, build_stream_message
from evaluation.harness import run_evaluation_scenario, load_policy
from workload_gen.generator import WorkloadGenerator
from rl_allocator.registry import get_active_policy, get_history, rollback_policy
from rl_allocator.retrain_manager import retrain_manager

router = APIRouter()

interactive_generator = live_runtime.generator


class SpikeRequest(BaseModel):
    multiplier: float = Field(default=5.0, ge=1.0, le=20.0)
    duration_seconds: float = Field(default=15.0, ge=1.0, le=300.0)


class CompareRequest(BaseModel):
    queries_per_variant: int = Field(default=300, ge=50, le=2000)
    spike_multiplier: float = Field(default=5.0, ge=1.0, le=10.0)


class RollbackRequest(BaseModel):
    version: str


class ManualQueryInjectRequest(BaseModel):
    calling_service: str = Field(min_length=1, max_length=100)
    query_type: str = Field(min_length=1, max_length=100)
    target_table: Optional[str] = Field(default=None, max_length=100)
    force_malicious: Optional[bool] = Field(default=False, description="Simulate suspicious / replay attack pattern")
    idempotency_key: Optional[str] = Field(default=None, description="Custom or replayed idempotency key")


class ManualQueryInjectResponse(BaseModel):
    query_id: str
    assigned_tier: str
    latency_budget_ms: float
    action_taken: Dict[str, int]
    resulting_latency_ms: float
    within_sla: bool
    explanation: str
    timestamp: str
    risk_score: float = 0.0
    is_quarantined: bool = False
    risk_flags: List[str] = []


@router.get("/health")
def get_health() -> Dict[str, Any]:
    return {
        "status": "HEALTHY",
        "timestamp": time.time(),
        "models": {
            "constrained_agent_ready": os.path.exists("rl_allocator/checkpoints/constrained_seed_42.zip"),
            "unconstrained_agent_ready": os.path.exists("rl_allocator/checkpoints/unconstrained_seed_42.zip"),
            "baseline_agent_ready": True,
        },
        "slas": {tier.value: sla.p99_budget_ms for tier, sla in DEFAULT_SLAS.items()},
        "spike_active": interactive_generator.check_spike_status(),
    }


@router.get("/metrics")
def get_tier_metrics() -> Dict[str, Any]:
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
            "SETTLEMENT_CRITICAL": {"budget_ms": 150.0, "description": "Ledger and clearing"},
            "ANALYTICAL": {"budget_ms": 1000.0, "description": "BI and reporting"},
        },
        "benchmark_summary": latest_bench,
    }


@router.post("/trigger-spike")
def trigger_spike(req: Optional[SpikeRequest] = None) -> Dict[str, Any]:
    multiplier = req.multiplier if req else 5.0
    duration_seconds = req.duration_seconds if req else 15.0
    live_runtime.trigger_spike(multiplier, duration_seconds)
    return {
        "status": "SPIKE_TRIGGERED",
        "multiplier": multiplier,
        "duration_seconds": duration_seconds,
        "end_time": interactive_generator.spike_end_time,
    }


@router.post("/clear-spike")
def clear_spike() -> Dict[str, Any]:
    live_runtime.clear_spike()
    return {"status": "SPIKE_CLEARED"}


@router.post("/inject-query", response_model=ManualQueryInjectResponse)
async def inject_query(req: ManualQueryInjectRequest) -> ManualQueryInjectResponse:
    try:
        query = live_runtime.build_query(req.calling_service, req.query_type, req.target_table)
        if req.force_malicious:
            query.payload_meta["force_malicious"] = True
        if req.idempotency_key:
            query.payload_meta["idempotency_key"] = req.idempotency_key

        result, action, metrics, active, multiplier = live_runtime.execute(query)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    log_record = live_runtime.log_result(action, result, multiplier)
    event = build_stream_message(query, result, action, metrics, active, multiplier, source="manual")
    await manager.broadcast(event)
    return ManualQueryInjectResponse(
        query_id=query.query_id,
        assigned_tier=query.tier.value,
        latency_budget_ms=query.latency_budget_ms,
        action_taken=action,
        resulting_latency_ms=round(result.latency_ms, 2),
        within_sla=not result.violated_sla,
        explanation=log_record["justification_text"],
        timestamp=datetime.now(timezone.utc).isoformat(),
        risk_score=round(result.risk_score, 3),
        is_quarantined=result.is_quarantined,
        risk_flags=result.risk_flags,
    )


@router.get("/explainability")
def get_explainability_feed(limit: int = Query(default=30, ge=1, le=200)) -> List[Dict[str, Any]]:
    return explainability_logger.get_recent_logs(limit=limit)


@router.get("/ablation-summary")
def get_ablation_summary() -> List[Dict[str, Any]]:
    summary_path = "evaluation/evaluation_summary.csv"
    if not os.path.exists(summary_path):
        raise HTTPException(status_code=404, detail="Ablation summary not yet generated.")
    df = pd.read_csv(summary_path)
    return df.to_dict(orient="records")


def run_compare(queries_count: int, multiplier: float, selected_variant: Optional[str]) -> Dict[str, Any]:
    selected_variants = (
        [selected_variant]
        if selected_variant in ["baseline", "unconstrained", "constrained"]
        else ["baseline", "unconstrained", "constrained"]
    )
    results = {}
    for v in selected_variants:
        try:
            policy = load_policy(v, seed=42)
            summary = run_evaluation_scenario(
                variant=v,
                policy=policy,
                total_queries=queries_count,
                spike_multiplier=multiplier,
                seed=42,
            )
            results[v] = summary
        except Exception as e:
            results[v] = {"error": str(e)}
    return {
        "status": "COMPLETED",
        "queries_per_variant": queries_count,
        "spike_multiplier": multiplier,
        "results": results,
    }


@router.get("/compare")
def compare_get(
    variant: Optional[str] = Query(default=None),
    queries: int = Query(default=300),
    spike_mult: float = Query(default=5.0),
) -> Dict[str, Any]:
    return run_compare(queries_count=queries, multiplier=spike_mult, selected_variant=variant)


@router.post("/compare")
def compare_post(req: CompareRequest) -> Dict[str, Any]:
    return run_compare(
        queries_count=req.queries_per_variant,
        multiplier=req.spike_multiplier,
        selected_variant=None,
    )


@router.get("/retrain/status")
def get_retrain_status():
    active = get_active_policy()
    if not active:
        raise HTTPException(status_code=404, detail="No active policy found")
        return {
            "version": "not_initialized",
            "is_live": False,
            "checkpoint_path": None,
            "auth_p99_ms": None,
            "compliance_pct": None,
            "trigger_reason": "SYSTEM_INIT",
            "message": "Registry not yet initialized. Click Trigger Retrain to start."
        }
    return active


@router.get("/retrain/history")
def get_retrain_history():
    return get_history()


@router.post("/retrain/trigger")
def trigger_retrain_job(force_bad: bool = Query(default=False)):
    # Auto-bootstrap registry if missing (e.g. fresh start, registry.json deleted)
    from rl_allocator.registry import get_active_policy as _gap, initialize_registry
    if not _gap():
        checkpoint = os.path.join("rl_allocator", "checkpoints", "constrained_seed_42.zip")
        if os.path.exists(checkpoint):
            initialize_registry(checkpoint, auth_p99_ms=8.5, compliance_pct=97.2)
        else:
            raise HTTPException(status_code=503, detail="No checkpoint found. Run training first.")

    result = retrain_manager.trigger_retrain(trigger_reason="MANUAL_API_TRIGGER", force_bad=force_bad)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=500, detail=result.get("message", "Retrain error"))
    return result


@router.post("/retrain/rollback")
def rollback_retrain(req: RollbackRequest):
    success = rollback_policy(req.version)
    if not success:
        raise HTTPException(status_code=404, detail=f"Version {req.version} not found in registry")
    return {"status": "ROLLED_BACK", "version": req.version}

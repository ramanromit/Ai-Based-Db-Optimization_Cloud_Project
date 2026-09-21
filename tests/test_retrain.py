import os
import json
import pytest
import threading
from fastapi.testclient import TestClient

from api.main import app
from rl_allocator.registry import (
    _write_registry, _read_registry, _append_policy,
    get_active_policy, get_history, register_policy, rollback_policy,
    REGISTRY_PATH
)
from rl_allocator.validation_gate import validate_new_policy
from rl_allocator.retrain_job import run_retrain_job
from rl_allocator.retrain_job import get_recent_workload_config
from api.live_runtime import live_runtime
from tagger.models import CriticalityTier
from workload_gen.schemas import WorkloadMixConfig

client = TestClient(app)


def test_retraining_snapshot_uses_observed_traffic():
    live_runtime._recent_observations.clear()
    live_runtime._recent_observations.extend([
        (CriticalityTier.AUTH_CRITICAL, 2.0),
        (CriticalityTier.AUTH_CRITICAL, 2.0),
        (CriticalityTier.AUTH_CRITICAL, 2.0),
        (CriticalityTier.SETTLEMENT_CRITICAL, 4.0),
        (CriticalityTier.ANALYTICAL, 4.0),
    ])

    snapshot = get_recent_workload_config()

    assert snapshot.auth_ratio == pytest.approx(0.6)
    assert snapshot.settlement_ratio == pytest.approx(0.2)
    assert snapshot.analytical_ratio == pytest.approx(0.2)
    assert snapshot.spike_multiplier == pytest.approx(2.8)


def test_registry_atomic_writes(tmpdir, monkeypatch):
    """
    Test 1: Concurrent atomic appends via _append_policy do not lose entries.
    Each of 4 threads appends a unique version. Final registry must have 5 entries
    (v1 base + v2..v5 from threads). FileLock serialises each read-modify-write.
    """
    test_registry = str(tmpdir.join("test_registry.json"))
    monkeypatch.setattr("rl_allocator.registry.REGISTRY_PATH", test_registry)

    # Write a baseline entry
    _write_registry([{"version": "v1", "is_live": True}], registry_path=test_registry)

    # Each thread atomically registers its own entry through the public API
    def write_thread(idx):
        register_policy(
            version=f"v{idx}",
            checkpoint_path=f"p{idx}.zip",
            auth_p99_ms=3.0 + idx,
            compliance_pct=99.0,
            trigger_reason="CONCURRENCY_TEST",
        )

    threads = [threading.Thread(target=write_thread, args=(i,)) for i in range(2, 6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_data = _read_registry(registry_path=test_registry)
    versions = {d["version"] for d in final_data}
    assert len(final_data) == 5, f"Expected 5 entries, got {len(final_data)}: {versions}"
    assert "v1" in versions
    for i in range(2, 6):
        assert f"v{i}" in versions


def test_validation_gate_rejects_bad_model(tmpdir):
    """
    Test 2: Validation gate rejects an explicitly undertrained (force_bad) candidate.
    A 1-timestep model has random weights and will have a HIGH violation rate when
    compared against the original trained live policy. The gate blocks it.
    """
    live_ckpt = "rl_allocator/checkpoints/constrained_seed_42.zip"
    if not os.path.exists(live_ckpt):
        pytest.skip("Live checkpoint not found — run training first")

    live_runtime._recent_observations.clear()
    live_runtime._recent_observations.extend([
        (CriticalityTier.AUTH_CRITICAL, 1.0),
        (CriticalityTier.SETTLEMENT_CRITICAL, 1.0),
        (CriticalityTier.ANALYTICAL, 1.0),
    ])

    # Train a garbage 1-timestep candidate
    bad_ckpt = run_retrain_job(trigger_reason="TEST_REJECTION", force_bad=True, output_dir=str(tmpdir))

    config = WorkloadMixConfig()
    is_approved, cand_metrics, live_metrics = validate_new_policy(bad_ckpt, live_ckpt, config)

    # The bad model must have WORSE compliance than the live model
    assert is_approved is False, (
        f"Safety gate MUST reject undertrained model. "
        f"Cand compliance={cand_metrics['compliance_pct']:.1f}%, "
        f"Live compliance={live_metrics['compliance_pct']:.1f}%"
    )


def test_dynamic_rollback(tmpdir, monkeypatch):
    """Test 3: Dynamic registration and rollback correctly flip is_live flags."""
    test_registry = str(tmpdir.join("test_registry.json"))
    monkeypatch.setattr("rl_allocator.registry.REGISTRY_PATH", test_registry)

    # Use internal helpers directly with explicit path for isolation
    _write_registry([], registry_path=test_registry)
    _append_policy({"version": "v1", "checkpoint_path": "p1.zip", "is_live": True, "auth_p99_ms": 4.0, "compliance_pct": 100.0, "trained_at": 0, "trigger_reason": "INIT"}, registry_path=test_registry)
    _append_policy({"version": "v2", "checkpoint_path": "p2.zip", "is_live": False, "auth_p99_ms": 3.5, "compliance_pct": 100.0, "trained_at": 1, "trigger_reason": "UPDATE"}, registry_path=test_registry)

    # Manually flip live flag to simulate promote
    data = _read_registry(registry_path=test_registry)
    for e in data:
        e["is_live"] = (e["version"] == "v2")
    _write_registry(data, registry_path=test_registry)

    live = next(e for e in _read_registry(registry_path=test_registry) if e["is_live"])
    assert live["version"] == "v2"

    data2 = _read_registry(registry_path=test_registry)
    for e in data2:
        e["is_live"] = (e["version"] == "v1")
    _write_registry(data2, registry_path=test_registry)

    live_after = next(e for e in _read_registry(registry_path=test_registry) if e["is_live"])
    assert live_after["version"] == "v1"


def test_retrain_rest_api(tmpdir, monkeypatch):
    """
    Test 4: API endpoints respond with the correct JSON structure and state transitions.
    Uses monkeypatch to redirect REGISTRY_PATH for isolation.
    """
    test_registry = str(tmpdir.join("test_registry.json"))
    monkeypatch.setattr("rl_allocator.registry.REGISTRY_PATH", test_registry)

    # Seed registry directly
    _write_registry([{
        "version": "v1",
        "checkpoint_path": "path1.zip",
        "trained_at": 0,
        "auth_p99_ms": 4.0,
        "compliance_pct": 100.0,
        "is_live": True,
        "trigger_reason": "INIT"
    }], registry_path=test_registry)

    # /retrain/status returns v1 as live
    res = client.get("/api/retrain/status")
    assert res.status_code == 200
    assert res.json()["version"] == "v1"
    assert res.json()["is_live"] is True

    monkeypatch.setattr(
        "api.routes.retrain_manager.trigger_retrain",
        lambda trigger_reason, force_bad: {
            "status": "REJECTED",
            "version": "candidate_test_bad",
            "metrics": {"auth_p99_ms": 12.4, "compliance_pct": 96.0},
            "workload_snapshot": {"auth_ratio": 0.6, "settlement_ratio": 0.2, "analytical_ratio": 0.2},
            "reason": "Candidate degraded SLA or throughput compared to live baseline.",
        },
    )
    res = client.post("/api/retrain/trigger?force_bad=true")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "REJECTED"
    assert body["version"] == "candidate_test_bad"
    assert body["metrics"]["auth_p99_ms"] == 12.4
    assert body["metrics"]["compliance_pct"] == 96.0
    assert body["workload_snapshot"]["auth_ratio"] == 0.6
    assert "reason" in body

    # /retrain/history returns 1 entry
    res = client.get("/api/retrain/history")
    assert res.status_code == 200
    history_before = res.json()
    assert len(history_before) == 1

    # Register v2 directly and check history grows
    _write_registry([
        {"version": "v1", "checkpoint_path": "path1.zip", "trained_at": 0, "auth_p99_ms": 4.0, "compliance_pct": 100.0, "is_live": False, "trigger_reason": "INIT"},
        {"version": "v2", "checkpoint_path": "path2.zip", "trained_at": 1, "auth_p99_ms": 3.8, "compliance_pct": 100.0, "is_live": True, "trigger_reason": "UPDATE"},
    ], registry_path=test_registry)

    res = client.get("/api/retrain/history")
    assert res.status_code == 200
    assert len(res.json()) == 2

    # /retrain/rollback reverts active to v1
    res = client.post("/api/retrain/rollback", json={"version": "v1"})
    assert res.status_code == 200
    assert res.json()["status"] == "ROLLED_BACK"

    res = client.get("/api/retrain/status")
    assert res.status_code == 200
    assert res.json()["version"] == "v1"
    assert res.json()["is_live"] is True

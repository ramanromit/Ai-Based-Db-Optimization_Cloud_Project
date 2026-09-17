import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "stream_endpoint" in data
    assert "endpoints" in data

def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "models" in data
    assert data["models"]["baseline_agent_ready"] is True

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "slas" in data
    assert data["slas"]["AUTH_CRITICAL"]["budget_ms"] == 10.0

def test_trigger_and_clear_spike():
    resp_trigger = client.post("/api/trigger-spike", json={"multiplier": 4.0, "duration_seconds": 10.0})
    resp_trigger = client.post("/trigger-spike", json={"multiplier": 4.0, "duration_seconds": 10.0})
    assert resp_trigger.status_code == 200
    assert resp_trigger.json()["status"] == "SPIKE_TRIGGERED"
    
    resp_clear = client.post("/api/clear-spike")
    resp_clear = client.post("/clear-spike")
    assert resp_clear.status_code == 200
    assert resp_clear.json()["status"] == "SPIKE_CLEARED"

def test_explainability_feed():
    response = client.get("/api/explainability?limit=5")
    response = client.get("/explainability?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_compare_endpoint_get_and_post():
    resp_get = client.get("/compare?variant=constrained&queries=50")
    assert resp_get.status_code == 200
    assert resp_get.json()["status"] == "COMPLETED"
    
    resp_post = client.post("/compare", json={"queries_per_variant": 50, "spike_multiplier": 3.0})
    assert resp_post.status_code == 200
    assert resp_post.json()["status"] == "COMPLETED"

def test_ablation_summary():
    response = client.get("/api/ablation-summary")
    response = client.get("/ablation-summary")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Verify presence of all three variants in summary
    variants = {item["variant"] for item in data}
    assert "baseline" in variants
    assert "constrained" in variants
    assert "unconstrained" in variants


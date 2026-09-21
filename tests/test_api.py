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


def test_manual_injection_tags_checkout_service():
    response = client.post("/api/inject-query", json={
        "calling_service": "checkout-service",
        "query_type": "balance_check",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_tier"] == "AUTH_CRITICAL"
    assert data["latency_budget_ms"] == 10.0
    assert "explanation" in data
    assert data["action_taken"]["pool_priority"] in (0, 1, 2)


def test_manual_injection_tags_reporting_service():
    response = client.post("/inject-query", json={
        "calling_service": "reporting-service",
        "query_type": "merchant_daily_summary",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_tier"] == "ANALYTICAL"
    assert data["latency_budget_ms"] == 1000.0


def test_manual_injection_uses_active_variant():
    constrained = client.post("/inject-query", json={
        "calling_service": "checkout-service",
        "query_type": "balance_check",
    })
    assert constrained.status_code == 200

    with client.websocket_connect("/ws/stream") as websocket:
        websocket.receive_json()
        websocket.send_json({"command": "set_variant", "variant": "baseline"})
        notification = websocket.receive_json()
        while notification.get("type") != "SYSTEM_NOTIFICATION":
            notification = websocket.receive_json()
        assert "BASELINE" in notification["message"]

    baseline = client.post("/inject-query", json={
        "calling_service": "checkout-service",
        "query_type": "balance_check",
    })
    assert baseline.status_code == 200
    assert baseline.json()["action_taken"] != constrained.json()["action_taken"]

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


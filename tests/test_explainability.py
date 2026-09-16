import pytest
import time
import os
from explainability.logger import ExplainabilityLogger
from explainability.templates import generate_justification

def test_generate_justification_text():
    action = {
        "pool_priority": 2,
        "replica_routing": 1,
        "cache_ttl": 2,
        "analytical_throttle": 2
    }
    text = generate_justification(
        variant="constrained",
        action=action,
        auth_p99=6.5,
        budget_ms=10.0,
        spike_factor=4.5,
        queue_saturation=0.8
    )
    
    assert "Traffic Spike" in text
    assert "Auth-critical SLA compliance maintained" in text
    assert "Reserved 80% dedicated connection pool" in text
    assert "CMDP Lagrangian constraint" in text

def test_explainability_logger_async_writes(tmp_path):
    db_file = str(tmp_path / "test_explainability.sqlite")
    jsonl_file = str(tmp_path / "test_audit.jsonl")
    
    logger = ExplainabilityLogger(db_path=db_file, jsonl_path=jsonl_file)
    
    action = {"pool_priority": 1, "replica_routing": 0, "cache_ttl": 1, "analytical_throttle": 0}
    record = logger.log_decision(
        variant="baseline",
        action=action,
        auth_p99_ms=12.4,
        sla_budget_ms=10.0,
        load_multiplier=3.0,
        queue_saturation=0.5
    )
    
    assert record["sla_violated"] is True
    assert "WARNING: Auth SLA breached" in record["justification_text"]
    
    # Allow background worker to flush
    time.sleep(0.5)
    
    logs = logger.get_recent_logs(limit=10)
    assert len(logs) >= 1
    assert logs[0]["variant"] == "baseline"


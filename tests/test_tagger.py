import pytest
from tagger.models import CriticalityTier
from tagger.tagger import tag_calling_service, get_tier_sla

def test_structural_tagging_known_services():
    # Auth-critical services
    assert tag_calling_service("payment-auth-service") == CriticalityTier.AUTH_CRITICAL
    assert tag_calling_service("fraud-screening-service") == CriticalityTier.AUTH_CRITICAL
    assert tag_calling_service("idempotency-service") == CriticalityTier.AUTH_CRITICAL
    
    # Settlement-critical services
    assert tag_calling_service("settlement-batch-service") == CriticalityTier.SETTLEMENT_CRITICAL
    assert tag_calling_service("clearing-engine") == CriticalityTier.SETTLEMENT_CRITICAL
    assert tag_calling_service("ledger-service") == CriticalityTier.SETTLEMENT_CRITICAL
    
    # Analytical services
    assert tag_calling_service("merchant-reporting-service") == CriticalityTier.ANALYTICAL
    assert tag_calling_service("risk-analytics-engine") == CriticalityTier.ANALYTICAL
    assert tag_calling_service("bi-query-service") == CriticalityTier.ANALYTICAL

def test_structural_tagging_prefix_patterns():
    assert tag_calling_service("auth-worker-node-12") == CriticalityTier.AUTH_CRITICAL
    assert tag_calling_service("fraud-detector-v2") == CriticalityTier.AUTH_CRITICAL
    assert tag_calling_service("settle-stream-processor") == CriticalityTier.SETTLEMENT_CRITICAL
    assert tag_calling_service("reconcil-hourly-cron") == CriticalityTier.SETTLEMENT_CRITICAL
    assert tag_calling_service("analytics-dashboard-api") == CriticalityTier.ANALYTICAL
    assert tag_calling_service("report-generator-daily") == CriticalityTier.ANALYTICAL

def test_tagging_header_override():
    headers = {"x-criticality-tier": "AUTH_CRITICAL"}
    # Even if unknown service name, trusted proxy header can specify
    assert tag_calling_service("random-proxy-service", client_headers=headers) == CriticalityTier.AUTH_CRITICAL

def test_tagging_fallback_to_analytical():
    assert tag_calling_service("unknown-third-party-tool") == CriticalityTier.ANALYTICAL

def test_tier_sla_budgets():
    auth_sla = get_tier_sla(CriticalityTier.AUTH_CRITICAL)
    assert auth_sla.p99_budget_ms == 10.0
    
    settle_sla = get_tier_sla(CriticalityTier.SETTLEMENT_CRITICAL)
    assert settle_sla.p99_budget_ms == 150.0
    
    analyt_sla = get_tier_sla(CriticalityTier.ANALYTICAL)
    assert analyt_sla.p99_budget_ms == 1000.0

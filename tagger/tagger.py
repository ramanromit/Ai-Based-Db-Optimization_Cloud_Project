import re
from typing import Optional, Dict, Any
from tagger.models import CriticalityTier, DEFAULT_SLAS, TierSLAConfig

# Structural service mapping table (O(1) dictionary lookup)
SERVICE_TO_TIER_MAP: Dict[str, CriticalityTier] = {
    # Auth-Critical services (P0)
    "payment-auth-service": CriticalityTier.AUTH_CRITICAL,
    "payment-gateway": CriticalityTier.AUTH_CRITICAL,
    "fraud-screening-service": CriticalityTier.AUTH_CRITICAL,
    "idempotency-service": CriticalityTier.AUTH_CRITICAL,
    "card-validator": CriticalityTier.AUTH_CRITICAL,
    "token-vault": CriticalityTier.AUTH_CRITICAL,
    "account-balance-service": CriticalityTier.AUTH_CRITICAL,

    # Settlement-Critical services (P1)
    "settlement-batch-service": CriticalityTier.SETTLEMENT_CRITICAL,
    "clearing-engine": CriticalityTier.SETTLEMENT_CRITICAL,
    "ledger-service": CriticalityTier.SETTLEMENT_CRITICAL,
    "reconciliation-worker": CriticalityTier.SETTLEMENT_CRITICAL,
    "ach-processor": CriticalityTier.SETTLEMENT_CRITICAL,
    "chargeback-processor": CriticalityTier.SETTLEMENT_CRITICAL,

    # Analytical services (P2)
    "merchant-reporting-service": CriticalityTier.ANALYTICAL,
    "risk-analytics-engine": CriticalityTier.ANALYTICAL,
    "bi-query-service": CriticalityTier.ANALYTICAL,
    "audit-exporter": CriticalityTier.ANALYTICAL,
    "compliance-reporting": CriticalityTier.ANALYTICAL,
    "batch-etl-loader": CriticalityTier.ANALYTICAL,
}

# Prefix patterns for dynamically named service instances (e.g. auth-service-prod-us-east-1)
PREFIX_PATTERNS = [
    (re.compile(r"^(auth|payment-auth|fraud|idempotency|token|card-val)", re.IGNORECASE), CriticalityTier.AUTH_CRITICAL),
    (re.compile(r"^(settle|clearing|ledger|reconcil|ach|chargeback)", re.IGNORECASE), CriticalityTier.SETTLEMENT_CRITICAL),
    (re.compile(r"^(report|bi-|analytics|audit|etl|stats|summary)", re.IGNORECASE), CriticalityTier.ANALYTICAL),
]

def tag_calling_service(service_name: str, client_headers: Optional[Dict[str, Any]] = None) -> CriticalityTier:
    """
    Tags an incoming query request based strictly on structural caller metadata.
    Does NOT inspect query SQL or transaction payloads to preserve security posture.
    
    Order of precedence:
    1. Explicit 'x-criticality-tier' header if trusted internal proxy
    2. Direct match in SERVICE_TO_TIER_MAP
    3. Regex prefix heuristic on service_name
    4. Default fallback: ANALYTICAL (safe degradation principle)
    """
    if client_headers and "x-criticality-tier" in client_headers:
        header_val = str(client_headers["x-criticality-tier"]).upper()
        if header_val in CriticalityTier.__members__:
            return CriticalityTier(header_val)

    normalized_name = service_name.strip().lower()
    
    # 1. Exact match
    if normalized_name in SERVICE_TO_TIER_MAP:
        return SERVICE_TO_TIER_MAP[normalized_name]

    # 2. Prefix pattern match
    for pattern, tier in PREFIX_PATTERNS:
        if pattern.search(normalized_name):
            return tier

    # 3. Fallback to analytical
    return CriticalityTier.ANALYTICAL

def get_tier_sla(tier: CriticalityTier) -> TierSLAConfig:
    """Returns SLA budget specifications for the given tier."""
    return DEFAULT_SLAS.get(tier, DEFAULT_SLAS[CriticalityTier.ANALYTICAL])


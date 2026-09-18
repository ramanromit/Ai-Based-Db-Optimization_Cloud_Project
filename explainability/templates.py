from typing import Dict, Any

def generate_justification(
    variant: str,
    action: Dict[str, Any],
    auth_p99: float,
    budget_ms: float,
    spike_factor: float,
    queue_saturation: float
) -> str:
    """
    Generates human-readable, auditable justification for autonomous DB resource decisions.
    Off the hot path; matches AWS Well-Architected Operational Excellence & Reliability pillars.
    """
    if variant == "RETRAIN_MANAGER":
        act = action.get("action")
        version = action.get("version")
        if act == "PROMOTED":
            return f"Retrained policy {version} passed safety gates (Auth P99 {auth_p99:.2f}ms <= {budget_ms:.2f}ms) under {spike_factor:.1f}x load and was promoted to live."
        else:
            return f"Retrained policy {version} REJECTED by safety gate (Auth P99 {auth_p99:.2f}ms) under {spike_factor:.1f}x load for degrading SLA compliance compared to live baseline."

    pool_priority = action.get("pool_priority", 0)
    replica_routing = action.get("replica_routing", 0)
    cache_ttl = action.get("cache_ttl", 1)
    analytical_throttle = action.get("analytical_throttle", 0)
    
    headroom = budget_ms - auth_p99
    is_spike = spike_factor > 1.2
    
    parts = []
    
    # 1. State Context
    if is_spike:
        parts.append(f"[Traffic Spike: {spike_factor:.1f}x normal load, Primary saturation: {queue_saturation*100:.0f}%]")
    else:
        parts.append(f"[Normal Traffic, Auth p99: {auth_p99:.2f}ms]")

    # 2. SLA Margin Context
    if headroom >= 0:
        parts.append(f"Auth-critical SLA compliance maintained with {headroom:.1f}ms headroom (budget: {budget_ms:.1f}ms).")
    else:
        parts.append(f"WARNING: Auth SLA breached by {abs(headroom):.1f}ms!")

    # 3. Action Rationales
    actions_desc = []
    if pool_priority == 2:
        actions_desc.append("Reserved 80% dedicated connection pool for Auth queries to prevent head-of-line queuing")
    elif pool_priority == 1:
        actions_desc.append("Allocated 50% priority pool reservation for Auth path")
    else:
        actions_desc.append("Maintained shared FIFO connection pool across all tiers")

    if replica_routing == 1:
        actions_desc.append("offloaded analytical scans to Read Replicas")
    elif replica_routing == 2:
        actions_desc.append("directed critical traffic to Primary instance")

    if cache_ttl == 2:
        actions_desc.append("extended Redis hot-path cache TTL to 300s to absorb burst reads")
    elif cache_ttl == 0:
        actions_desc.append("bypassed cache layer")

    if analytical_throttle == 2:
        actions_desc.append("heavily throttled analytical background queries (75% delay) to shed Primary compute load")
    elif analytical_throttle == 1:
        actions_desc.append("moderately throttled analytical reporting (25% delay)")

    if actions_desc:
        parts.append("Actions enacted: " + "; ".join(actions_desc) + ".")

    # 4. Strategic Justification
    if variant.lower() == "constrained":
        if is_spike:
            parts.append("Policy rationale: CMDP Lagrangian constraint actively enforcing P(Auth p99 <= 10ms) by shedding non-critical analytical resources.")
        else:
            parts.append("Policy rationale: Operating in optimal cost-latency state with stable SLA headroom.")
    elif variant.lower() == "unconstrained":
        parts.append("Policy rationale: Unconstrained RL optimizing overall cluster throughput without hard tier SLA bounds.")
    else: # baseline
        parts.append("Policy rationale: Criticality-agnostic round-robin baseline treating all queries with equal priority.")

    return " ".join(parts)


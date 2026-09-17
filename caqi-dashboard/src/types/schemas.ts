export type CriticalityTier = 'AUTH_CRITICAL' | 'SETTLEMENT_CRITICAL' | 'ANALYTICAL';

export type AllocatorVariant = 'baseline' | 'unconstrained' | 'constrained';

export interface ActionPayload {
  pool_priority: number;
  replica_routing: number;
  cache_ttl: number;
  analytical_throttle: number;
}

export interface RollingMetrics {
  auth_p99_ms: number;
  settle_p99_ms: number;
  analyt_p99_ms: number;
}

export interface PaymentPayloadMeta {
  account_id?: string;
  merchant_id?: string;
  transaction_amount?: number;
  card_network?: string;
  card_type?: string;
  fraud_risk_score?: number;
  dist1?: number;
  idempotency_key?: string;
}

export interface QueryProcessedEvent {
  type: 'QUERY_PROCESSED';
  query_id: string;
  timestamp: number;
  service_name: string;
  tier: CriticalityTier;
  query_type: string;
  latency_ms: number;
  sla_budget_ms: number;
  sla_violated: boolean;
  is_cache_hit: boolean;
  target_route: string;
  active_variant: AllocatorVariant;
  spike_active: boolean;
  payload_meta?: PaymentPayloadMeta;
  action: ActionPayload;
  rolling_metrics: RollingMetrics;
}

export interface SystemNotificationEvent {
  type: 'SYSTEM_NOTIFICATION';
  message: string;
}

export type WebSocketStreamMessage = QueryProcessedEvent | SystemNotificationEvent;

export interface ExplainabilityLog {
  timestamp: number;
  variant: string;
  load_multiplier: number;
  auth_p99_ms: number;
  sla_budget_ms: number;
  action: ActionPayload;
  sla_violated: boolean;
  justification_text: string;
}

export interface AblationSummaryItem {
  variant: AllocatorVariant;
  seed: number;
  auth_p50_ms: number;
  auth_p95_ms: number;
  auth_p99_ms: number;
  auth_sla_compliance_pct: number;
  auth_violations_count: number;
  settle_p99_ms: number;
  analyt_p99_ms: number;
  throughput_qps: number;
  avg_resource_cost: number;
  total_queries: number;
}

export interface HealthResponse {
  status: string;
  timestamp: number;
  models: {
    constrained_agent_ready: boolean;
    unconstrained_agent_ready: boolean;
    baseline_agent_ready: boolean;
  };
  slas: Record<string, number>;
  spike_active: boolean;
}

export interface MetricsResponse {
  timestamp: number;
  spike_active: boolean;
  slas: Record<string, { budget_ms: number; description: string }>;
  benchmark_summary: AblationSummaryItem[];
}

export interface CompareResponse {
  status: string;
  queries_per_variant: number;
  spike_multiplier: number;
  results: Record<string, AblationSummaryItem | { error: string }>;
}


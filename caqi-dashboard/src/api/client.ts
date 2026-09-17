import axios from 'axios';
import type {
  HealthResponse,
  MetricsResponse,
  ExplainabilityLog,
  AblationSummaryItem,
  CompareResponse
} from '../types/schemas';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getHealth = async (): Promise<HealthResponse> => {
  const { data } = await apiClient.get<HealthResponse>('/api/health');
  return data;
};

export const getMetrics = async (): Promise<MetricsResponse> => {
  const { data } = await apiClient.get<MetricsResponse>('/metrics');
  return data;
};

export const getExplainabilityFeed = async (limit: number = 30): Promise<ExplainabilityLog[]> => {
  const { data } = await apiClient.get<ExplainabilityLog[]>(`/explainability?limit=${limit}`);
  return data;
};

export const getAblationSummary = async (): Promise<AblationSummaryItem[]> => {
  const { data } = await apiClient.get<AblationSummaryItem[]>('/ablation-summary');
  return data;
};

export const triggerSpike = async (multiplier: number = 5.0, durationSeconds: number = 15.0) => {
  const { data } = await apiClient.post('/trigger-spike', {
    multiplier,
    duration_seconds: durationSeconds,
  });
  return data;
};

export const clearSpike = async () => {
  const { data } = await apiClient.post('/clear-spike');
  return data;
};

export const compareVariants = async (
  queries: number = 300,
  spikeMultiplier: number = 5.0,
  variant?: string
): Promise<CompareResponse> => {
  const url = variant ? `/compare?variant=${variant}&queries=${queries}&spike_mult=${spikeMultiplier}` : '/compare';
  const { data } = await apiClient.post<CompareResponse>(url, {
    queries_per_variant: queries,
    spike_multiplier: spikeMultiplier,
  });
  return data;
};


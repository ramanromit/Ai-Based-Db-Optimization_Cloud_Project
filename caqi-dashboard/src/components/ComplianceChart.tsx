import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
  Cell,
} from 'recharts';
import { Award, Download, RefreshCw } from 'lucide-react';
import { getAblationSummary } from '../api/client';
import { ErrorStateCard } from './ErrorStateCard';
import type { AblationSummaryItem } from '../types/schemas';

export const ComplianceChart: React.FC = () => {
  const { data, isLoading, isError, refetch } = useQuery<AblationSummaryItem[]>({
    queryKey: ['ablationSummary'],
    queryFn: getAblationSummary,
    staleTime: 10000,
    refetchInterval: 15000,
  });

  // Calculate averaged metrics per variant from real backend dataset
  const chartData = React.useMemo(() => {
    if (!data || data.length === 0) return [];

    const grouped: Record<string, { variant: string; name: string; auth_p99: number; compliance: number; count: number }> = {
      baseline: { variant: 'baseline', name: 'Aurora Baseline', auth_p99: 0, compliance: 0, count: 0 },
      unconstrained: { variant: 'unconstrained', name: 'Unconstrained RL', auth_p99: 0, compliance: 0, count: 0 },
      constrained: { variant: 'constrained', name: 'CAQI Constrained', auth_p99: 0, compliance: 0, count: 0 },
    };

    data.forEach((item) => {
      const v = item.variant.toLowerCase();
      if (grouped[v]) {
        grouped[v].auth_p99 += item.auth_p99_ms;
        grouped[v].compliance += item.auth_sla_compliance_pct;
        grouped[v].count += 1;
      }
    });

    return Object.values(grouped).map((g) => ({
      name: g.name,
      variant: g.variant,
      auth_p99: g.count > 0 ? parseFloat((g.auth_p99 / g.count).toFixed(2)) : 0,
      compliance: g.count > 0 ? parseFloat((g.compliance / g.count).toFixed(1)) : 0,
    }));
  }, [data]);

  const handleDownloadCSV = () => {
    if (!data) return;
    const headers = 'variant,seed,auth_p50_ms,auth_p95_ms,auth_p99_ms,auth_sla_compliance_pct,auth_violations_count,settle_p99_ms,analyt_p99_ms,throughput_qps\n';
    const rows = data
      .map(
        (r) =>
          `${r.variant},${r.seed},${r.auth_p50_ms},${r.auth_p95_ms},${r.auth_p99_ms},${r.auth_sla_compliance_pct},${r.auth_violations_count},${r.settle_p99_ms},${r.analyt_p99_ms},${r.throughput_qps}`
      )
      .join('\n');

    const blob = new Blob([headers + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'caqi_ablation_benchmark_results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isError) {
    return (
      <ErrorStateCard
        title="Failed to Load Benchmark Telemetry"
        message="Could not connect to FastAPI endpoint /api/ablation-summary."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-slate-800 rounded-lg text-emerald-400">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Ablation SLA Compliance Benchmark</h3>
            <p className="text-xs text-slate-400">Auth-Critical P99 Latency vs 10ms Budget (Real Evaluated Dataset)</p>
          </div>
        </div>

        <button
          onClick={handleDownloadCSV}
          disabled={!data || data.length === 0}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg transition-colors border border-slate-700 disabled:opacity-50"
        >
          <Download className="w-3.5 h-3.5 text-cyan-400" />
          <span>Export CSV</span>
        </button>
      </div>

      {isLoading ? (
        <div className="w-full h-64 flex items-center justify-center text-slate-400 text-xs space-x-2">
          <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
          <span>Loading backend evaluation dataset...</span>
        </div>
      ) : (
        <div className="w-full h-64 mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 20, right: 20, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2945" vertical={false} />
              <XAxis dataKey="name" stroke="#94a3b8" tick={{ fontSize: 11 }} />
              <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} label={{ value: 'P99 Latency (ms)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0d1322', borderColor: '#2b395b', borderRadius: '12px', fontSize: '12px' }}
                formatter={(value: any) => [`${value} ms`, 'Auth P99 Latency']}
              />
              <ReferenceLine y={10.0} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Auth SLA Budget: 10.0ms', fill: '#ef4444', fontSize: 11, position: 'top' }} />
              <Bar dataKey="auth_p99" radius={[8, 8, 0, 0]}>
                {chartData.map((entry, index) => {
                  const isViolated = entry.auth_p99 > 10.0;
                  const color = entry.variant === 'constrained' ? '#10b981' : isViolated ? '#ef4444' : '#f59e0b';
                  return <Cell key={`cell-${index}`} fill={color} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};


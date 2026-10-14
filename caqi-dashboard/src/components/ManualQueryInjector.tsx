import React, { useMemo, useState } from 'react';
import { CheckCircle2, Loader2, Send, ShieldAlert, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { injectQuery } from '../api/client';
import type { ManualQueryInjectResponse } from '../types/schemas';

const serviceOptions = [
  { value: 'checkout-service', label: 'Checkout service' },
  { value: 'settlement-batch', label: 'Settlement batch' },
  { value: 'reporting-service', label: 'Reporting service' },
];

const queryOptions: Record<string, { value: string; label: string }[]> = {
  'checkout-service': [
    { value: 'balance_check', label: 'Balance check' },
    { value: 'idempotency_lookup', label: 'Idempotency lookup' },
    { value: 'fraud_checkpoint', label: 'Fraud checkpoint' },
  ],
  'settlement-batch': [
    { value: 'ledger_entry', label: 'Ledger entry' },
    { value: 'batch_settlement', label: 'Batch settlement' },
    { value: 'reconciliation_query', label: 'Reconciliation query' },
  ],
  'reporting-service': [
    { value: 'merchant_daily_summary', label: 'Merchant daily summary' },
    { value: 'risk_aggregation', label: 'Risk aggregation' },
    { value: 'bi_volume_metrics', label: 'BI volume metrics' },
  ],
};

const defaultTables: Record<string, string> = {
  'checkout-service': 'accounts',
  'settlement-batch': 'transactions',
  'reporting-service': 'transactions',
};

export const ManualQueryInjector: React.FC = () => {
  const [service, setService] = useState('checkout-service');
  const [queryType, setQueryType] = useState('balance_check');
  const [targetTable, setTargetTable] = useState('');
  const [simulateMalicious, setSimulateMalicious] = useState(false);
  const [result, setResult] = useState<ManualQueryInjectResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const availableQueries = useMemo(() => queryOptions[service], [service]);

  const handleServiceChange = (nextService: string) => {
    setService(nextService);
    setQueryType(queryOptions[nextService][0].value);
    setTargetTable('');
    setError(null);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const nextResult = await injectQuery({
        calling_service: service,
        query_type: queryType,
        target_table: targetTable || undefined,
        force_malicious: simulateMalicious,
        idempotency_key: simulateMalicious ? 'idemp_replayed_malicious_token' : undefined,
      });
      setResult(nextResult);
    } catch (submitError: any) {
      setResult(null);
      setError(submitError?.response?.data?.detail || 'The live query could not be injected. Check the backend connection.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Manual Query Injection & Threat Simulation</h3>
          <p className="text-xs text-slate-400 mt-1">Test real-time routing, Lagrangian RL allocation, and security quarantine enforcement.</p>
        </div>
        <Send className="w-5 h-5 text-cyan-400" />
      </div>

      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <label className="text-xs text-slate-400">
          Calling service
          <select value={service} onChange={(event) => handleServiceChange(event.target.value)} className="mt-1 w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-slate-200">
            {serviceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-400">
          Query type
          <select value={queryType} onChange={(event) => setQueryType(event.target.value)} className="mt-1 w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-slate-200">
            {availableQueries.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-400">
          Target table <span className="text-slate-600">(optional)</span>
          <input value={targetTable} onChange={(event) => setTargetTable(event.target.value)} placeholder={`Defaults to ${defaultTables[service]}`} className="mt-1 w-full rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-slate-200 placeholder:text-slate-600" />
        </label>

        {/* Security Simulation Toggle */}
        <div className="md:col-span-3 flex items-center justify-between bg-slate-950/60 border border-slate-800 rounded-lg p-2.5 px-3.5 my-1">
          <div className="flex items-center space-x-2">
            <AlertTriangle className={`w-4 h-4 ${simulateMalicious ? 'text-rose-400' : 'text-slate-500'}`} />
            <div>
              <span className="text-xs font-semibold text-slate-200">Simulate Replay Attack / Malicious Critical Query</span>
              <p className="text-[11px] text-slate-400">Tests if CAQI correctly quarantines high-risk auth queries rather than granting priority.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSimulateMalicious(!simulateMalicious)}
            className={`px-3 py-1 rounded text-xs font-bold transition ${
              simulateMalicious 
                ? 'bg-rose-900/60 border border-rose-700 text-rose-200' 
                : 'bg-slate-800 border border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            {simulateMalicious ? 'ARMED (High Risk)' : 'Clean Query'}
          </button>
        </div>

        <button type="submit" disabled={isSubmitting} className="md:col-span-3 flex items-center justify-center gap-2 rounded-lg bg-cyan-500/20 border border-cyan-400/40 px-4 py-2.5 text-sm font-semibold text-cyan-200 hover:bg-cyan-500/30 disabled:opacity-50">
          {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          {isSubmitting ? 'Injecting...' : (simulateMalicious ? 'Inject Malicious Query' : 'Inject Live Query')}
        </button>
      </form>

      {error && (
        <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-200 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 shrink-0" />{error}
        </div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4 rounded-xl border border-cyan-400/40 bg-slate-950/80 p-4 text-xs">
          <div className="flex items-center justify-between mb-3">
            <span className="font-mono font-bold uppercase tracking-wider text-cyan-300">Injected Query - {service}</span>
            <div className="flex items-center space-x-2">
              {result.is_quarantined && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-950 text-rose-300 border border-rose-800">
                  Quarantined
                </span>
              )}
              {result.within_sla ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <ShieldAlert className="w-5 h-5 text-red-400" />}
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-slate-400">
            <span>Tagged as<strong className="block text-slate-100 mt-1">{result.assigned_tier}</strong></span>
            <span>Risk Score<strong className={`block mt-1 font-bold ${result.is_quarantined ? 'text-rose-400' : 'text-emerald-400'}`}>{(Number(result.risk_score || 0) * 100).toFixed(1)}%</strong></span>
            <span>Result<strong className={`block mt-1 ${result.within_sla ? 'text-emerald-400' : 'text-red-400'}`}>{result.resulting_latency_ms.toFixed(2)} ms</strong></span>
            <span>Pool / route<strong className="block text-slate-100 mt-1">{result.action_taken.pool_priority} / {result.action_taken.replica_routing}</strong></span>
          </div>
          <p className="mt-3 border-t border-slate-800 pt-3 leading-relaxed text-slate-300">{result.explanation}</p>
        </motion.div>
      )}
    </div>
  );
};

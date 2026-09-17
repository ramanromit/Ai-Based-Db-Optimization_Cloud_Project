import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, ShieldAlert, CheckCircle2, RefreshCw } from 'lucide-react';
import { getExplainabilityFeed } from '../api/client';
import { ErrorStateCard } from './ErrorStateCard';
import type { ExplainabilityLog } from '../types/schemas';

export const ExplainabilityFeed: React.FC = () => {
  const { data, isLoading, isError, refetch } = useQuery<ExplainabilityLog[]>({
    queryKey: ['explainabilityFeed'],
    queryFn: () => getExplainabilityFeed(25),
    staleTime: 4000,
    refetchInterval: 5000,
  });

  if (isError) {
    return (
      <ErrorStateCard
        title="Explainability Feed Disconnected"
        message="Unable to fetch audit logs from /api/explainability."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-slate-800 rounded-lg text-cyan-400">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Explainability Audit Stream</h3>
            <p className="text-xs text-slate-400">Async Natural-Language Decision Justifications (Off Hot Path)</p>
          </div>
        </div>

        <button
          onClick={() => refetch()}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors border border-slate-700"
          title="Refresh Audit Logs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {isLoading ? (
        <div className="w-full h-48 flex items-center justify-center text-slate-400 text-xs space-x-2">
          <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
          <span>Polling explainability engine...</span>
        </div>
      ) : (
        <div className="overflow-y-auto max-h-72 space-y-3 pr-1">
          <AnimatePresence>
            {data && data.length > 0 ? (
              data.map((log, index) => {
                const isViolation = log.sla_violated;
                const formattedTime = new Date(log.timestamp * 1000).toLocaleTimeString();

                return (
                  <motion.div
                    key={`${log.timestamp}-${index}`}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className={`p-3.5 rounded-xl border text-xs transition-all ${
                      isViolation
                        ? 'bg-red-500/10 border-red-500/30 text-red-200'
                        : 'bg-slate-950/70 border-slate-800/80 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5 font-mono text-[11px]">
                      <div className="flex items-center space-x-2">
                        {isViolation ? (
                          <ShieldAlert className="w-4 h-4 text-red-400" />
                        ) : (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        )}
                        <span className="font-semibold uppercase tracking-wider text-slate-200">{log.variant} Policy</span>
                        {log.load_multiplier > 1.2 && (
                          <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-[10px]">
                            {log.load_multiplier.toFixed(1)}x Load
                          </span>
                        )}
                      </div>
                      <span className="text-slate-400">{formattedTime}</span>
                    </div>

                    <p className="leading-relaxed font-sans text-slate-300 mt-1">{log.justification_text}</p>
                  </motion.div>
                );
              })
            ) : (
              <div className="text-center py-8 text-slate-500 text-xs">No audit logs recorded yet.</div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};


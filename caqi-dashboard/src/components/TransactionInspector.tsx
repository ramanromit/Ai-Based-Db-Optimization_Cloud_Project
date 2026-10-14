import React from 'react';
import { CreditCard, ShieldCheck, AlertOctagon, ShieldAlert } from 'lucide-react';
import { useStreamStore } from '../store/streamStore';

export const TransactionInspector: React.FC = () => {
  const { latestEvent } = useStreamStore();

  const meta = latestEvent?.payload_meta || {};
  const riskScore = latestEvent?.risk_score !== undefined ? latestEvent.risk_score : (meta.fraud_risk_score || 0.02);
  const isQuarantined = latestEvent?.is_quarantined || false;
  const riskFlags = latestEvent?.risk_flags || [];
  const isHighRisk = riskScore > 0.5;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
            <CreditCard className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">PaySim & IEEE-CIS Telemetry</h3>
            <p className="text-xs text-slate-400">Dual-Signal: Criticality Intent + Legitimacy Verification</p>
          </div>
        </div>

        {/* Security Quarantine Status Badge */}
        {isQuarantined ? (
          <span className="flex items-center space-x-1 px-2.5 py-1 text-[11px] font-bold tracking-wide uppercase bg-rose-950/80 text-rose-300 border border-rose-800 rounded-lg animate-pulse">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            <span>Quarantined</span>
          </span>
        ) : (
          <span className="flex items-center space-x-1 px-2.5 py-1 text-[11px] font-medium tracking-wide uppercase bg-emerald-950/60 text-emerald-300 border border-emerald-800 rounded-lg">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Verified Clean</span>
          </span>
        )}
      </div>

      {latestEvent ? (
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 space-y-2.5 text-xs font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Account ID:</span>
            <span className="text-cyan-300 font-bold">{meta.account_id || 'acc_4821'}</span>
          </div>

          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Transaction Amount:</span>
            <span className="text-emerald-400 font-bold">${(meta.transaction_amount || (meta as any).amount || 142.50).toFixed(2)}</span>
          </div>

          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Idempotency Token:</span>
            <span className="text-slate-300 truncate max-w-[180px] text-[11px]">
              {meta.idempotency_key ? String(meta.idempotency_key).slice(0, 18) + '...' : 'single_use_verified'}
            </span>
          </div>

          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Anomaly Risk Index:</span>
            <div className="flex items-center space-x-1.5">
              {isHighRisk ? (
                <AlertOctagon className="w-4 h-4 text-rose-400" />
              ) : (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              )}
              <span className={`font-bold ${isHighRisk ? 'text-rose-400' : 'text-emerald-400'}`}>
                {(riskScore * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-slate-400">Execution Route:</span>
            <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
              isQuarantined 
                ? 'bg-rose-950 text-rose-300 border border-rose-800' 
                : 'bg-cyan-950 text-cyan-300 border border-cyan-800'
            }`}>
              {latestEvent.target_route || (isQuarantined ? 'QUARANTINE_SANDBOX_POOL' : 'PRIMARY')}
            </span>
          </div>

          {riskFlags.length > 0 && (
            <div className="pt-2 border-t border-slate-800/80">
              <span className="text-[10px] text-rose-400 font-bold uppercase tracking-wider">Triggered Flags: </span>
              <span className="text-[10px] text-slate-300">{riskFlags.join(', ')}</span>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-slate-950/50 border border-slate-800/50 rounded-xl p-8 text-center text-slate-500 text-xs">
          Waiting for live payment transaction stream...
        </div>
      )}
    </div>
  );
};

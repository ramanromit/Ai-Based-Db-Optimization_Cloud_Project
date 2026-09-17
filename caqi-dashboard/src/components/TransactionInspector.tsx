import React from 'react';
import { CreditCard, ShieldCheck, AlertOctagon } from 'lucide-react';
import { useStreamStore } from '../store/streamStore';

export const TransactionInspector: React.FC = () => {
  const { latestEvent } = useStreamStore();

  const meta = latestEvent?.payload_meta || {};
  const isHighRisk = (meta.fraud_risk_score || 0) > 0.5;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between h-full">
      <div className="flex items-center space-x-2 mb-3">
        <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
          <CreditCard className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">IEEE-CIS Transaction Feature Stream</h3>
          <p className="text-xs text-slate-400">Live payment attributes (Tagged zero-payload at RDS Proxy)</p>
        </div>
      </div>

      {latestEvent ? (
        <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 space-y-2.5 text-xs font-mono">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Account ID:</span>
            <span className="text-cyan-300 font-bold">{meta.account_id || 'acc_4821'}</span>
          </div>

          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Transaction Amount:</span>
            <span className="text-emerald-400 font-bold">${meta.transaction_amount?.toFixed(2) || '142.50'}</span>
          </div>

          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Card Network / Type:</span>
            <span className="text-slate-200 capitalize">
              {meta.card_network || 'visa'} ({meta.card_type || 'debit'})
            </span>
          </div>

          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-slate-400">Distance Delta (dist1):</span>
            <span className="text-slate-300">{meta.dist1 || 12.4} miles</span>
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-slate-400">Fraud Risk Score:</span>
            <div className="flex items-center space-x-1.5">
              {isHighRisk ? (
                <AlertOctagon className="w-4 h-4 text-red-400" />
              ) : (
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
              )}
              <span className={`font-bold ${isHighRisk ? 'text-red-400' : 'text-emerald-400'}`}>
                {((meta.fraud_risk_score || 0.034) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-950/50 border border-slate-800/50 rounded-xl p-8 text-center text-slate-500 text-xs">
          Waiting for live payment transaction stream...
        </div>
      )}
    </div>
  );
};


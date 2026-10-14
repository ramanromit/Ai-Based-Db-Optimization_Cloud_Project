import React from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  Fingerprint, 
  Database, 
  Lock, 
  Activity 
} from 'lucide-react';
import { useStreamStore } from '../store/streamStore';
import { TransactionInspector } from './TransactionInspector';
import { ManualQueryInjector } from './ManualQueryInjector';

export const SecuritySection: React.FC = () => {
  const { latestEvent } = useStreamStore();
  const isCurrentThreat = latestEvent?.is_quarantined || false;

  return (
    <section className="bg-slate-900/90 border border-rose-500/30 rounded-2xl p-6 shadow-2xl relative overflow-hidden space-y-6">
      {/* Decorative gradient glow */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-rose-500/20 text-rose-400 rounded-xl border border-rose-500/30">
            <Fingerprint className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                Section 2: Security & Anomaly Detection Layer
              </h2>
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-rose-950 text-rose-300 border border-rose-800 rounded">
                PaySim + Replay Engine
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Dual-Signal Defense: Intent Criticality Tagging coupled with Real-Time Legitimacy Scoring.
            </p>
          </div>
        </div>

        {/* Live Security Threat Status Indicator */}
        <div className="flex items-center space-x-3">
          <div className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl border text-xs font-mono font-bold ${
            isCurrentThreat
              ? 'bg-rose-950/80 border-rose-700 text-rose-200 animate-pulse'
              : 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
          }`}>
            {isCurrentThreat ? <ShieldAlert className="w-4 h-4 text-rose-400" /> : <ShieldCheck className="w-4 h-4 text-emerald-400" />}
            <span>STATUS: {isCurrentThreat ? 'THREAT DETECTED (QUARANTINED)' : 'ALL TRAFFIC VERIFIED'}</span>
          </div>
        </div>
      </div>

      {/* Security Architecture Explainer Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-cyan-400">
            <Lock className="w-4 h-4" />
            <h4 className="text-xs font-bold uppercase tracking-wider">1. Idempotency Replay Guard</h4>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Tracks single-use transaction tokens across a sliding TTL window. Resubmitted keys trigger an immediate 
            <span className="text-rose-400 font-mono font-bold"> +0.75 risk surge</span>, preventing replay attacks from consuming resources.
          </p>
        </div>

        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-purple-400">
            <Activity className="w-4 h-4" />
            <h4 className="text-xs font-bold uppercase tracking-wider">2. PaySim Heuristic Profiler</h4>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Matches payment transfers against known PaySim fraud signatures—including sudden balance wipeouts 
            (<span className="text-slate-200 font-mono">old_bal = transfer & new_bal = 0</span>) and outlier transaction sizes.
          </p>
        </div>

        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-2">
          <div className="flex items-center space-x-2 text-rose-400">
            <Database className="w-4 h-4" />
            <h4 className="text-xs font-bold uppercase tracking-wider">3. Sandbox Quarantine Routing</h4>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            High-risk auth queries are denied access to the priority connection pool. Diverted to 
            <span className="text-rose-300 font-mono font-bold"> QUARANTINE_SANDBOX_POOL</span> with step-up verification overhead.
          </p>
        </div>
      </div>

      {/* Main Security Interactive Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Transaction Inspector & Feature Analyzer (5 cols) */}
        <div className="lg:col-span-5 h-full">
          <TransactionInspector />
        </div>

        {/* Right Column: Threat Simulation & Injection Controller (7 cols) */}
        <div className="lg:col-span-7">
          <ManualQueryInjector />
        </div>
      </div>
    </section>
  );
};

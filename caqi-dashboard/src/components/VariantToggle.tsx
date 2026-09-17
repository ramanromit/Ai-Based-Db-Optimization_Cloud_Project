import React from 'react';
import { Sliders, Shield, Zap, RefreshCw } from 'lucide-react';
import { useStreamStore } from '../store/streamStore';
import { useWebSocketStream } from '../hooks/useWebSocketStream';
import type { AllocatorVariant } from '../types/schemas';

export const VariantToggle: React.FC = () => {
  const { activeVariant } = useStreamStore();
  const { switchVariant } = useWebSocketStream();

  const options: { id: AllocatorVariant; label: string; sub: string; icon: any; color: string }[] = [
    {
      id: 'baseline',
      label: 'Aurora Baseline',
      sub: 'FIFO Shared Pool',
      icon: RefreshCw,
      color: 'text-red-400 border-red-500/40 bg-red-500/10',
    },
    {
      id: 'unconstrained',
      label: 'Unconstrained RL',
      sub: 'Throughput Maximizer',
      icon: Zap,
      color: 'text-amber-400 border-amber-500/40 bg-amber-500/10',
    },
    {
      id: 'constrained',
      label: 'Constrained CAQI',
      sub: 'Lagrangian SLA Agent',
      icon: Shield,
      color: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10',
    },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between h-full">
      <div className="flex items-center space-x-2 mb-3">
        <div className="p-2 bg-cyan-500/10 rounded-lg text-cyan-400">
          <Sliders className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Live Allocator Policy Driver</h3>
          <p className="text-xs text-slate-400">Switch live agent controlling proxy connection pools & cache TTL</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 mt-2">
        {options.map((opt) => {
          const isActive = activeVariant === opt.id;
          const Icon = opt.icon;

          return (
            <button
              key={opt.id}
              onClick={() => switchVariant(opt.id)}
              className={`p-3 rounded-xl border text-left transition-all flex items-center justify-between ${
                isActive
                  ? `${opt.color} shadow-lg shadow-black/40 ring-1 ring-cyan-500/50`
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className={`p-2 rounded-lg ${isActive ? 'bg-slate-900' : 'bg-slate-900/60'}`}>
                  <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                </div>
                <div>
                  <div className="text-xs font-bold text-slate-200">{opt.label}</div>
                  <div className="text-[10px] text-slate-400">{opt.sub}</div>
                </div>
              </div>

              {isActive && (
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 rounded">
                  ACTIVE
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};


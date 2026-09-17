import React from 'react';
import { ShieldCheck, Activity, Zap, Cpu } from 'lucide-react';
import { useStreamStore } from '../store/streamStore';

export const Header: React.FC = () => {
  const { isConnected, isSpikeActive, activeVariant } = useStreamStore();

  const variantLabels = {
    constrained: 'Constrained CAQI (Lagrangian SLA)',
    unconstrained: 'Unconstrained RL (Throughput Only)',
    baseline: 'Aurora Baseline (Criticality-Agnostic)',
  };

  return (
    <header className="bg-slate-900/90 backdrop-blur border-b border-slate-800 px-6 py-4 sticky top-0 z-50 shadow-lg">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* System Title */}
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-gradient-to-tr from-cyan-600 to-emerald-500 rounded-xl shadow-md text-slate-950 font-bold">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-white font-mono">CAQI Dashboard</h1>
              <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider bg-cyan-950 text-cyan-300 border border-cyan-800 rounded">
                Autonomous DB Engine
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Criticality-Aware Autonomous Query Intelligence for Online Payment Systems
            </p>
          </div>
        </div>

        {/* Live Controls & Telemetry Badges */}
        <div className="flex items-center space-x-3 text-xs">
          
          {/* Active Allocator Driver */}
          <div className="hidden lg:flex items-center space-x-2 bg-slate-950/70 border border-slate-800 px-3 py-1.5 rounded-lg">
            <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span className="text-slate-400">Driver:</span>
            <span className="font-semibold text-slate-200 capitalize font-mono">
              {variantLabels[activeVariant]}
            </span>
          </div>

          {/* Traffic Spike Indicator */}
          {isSpikeActive ? (
            <div className="flex items-center space-x-1.5 bg-red-500/10 border border-red-500/40 text-red-400 px-3 py-1.5 rounded-lg font-semibold animate-bounce">
              <Zap className="w-4 h-4 text-red-400 fill-current" />
              <span>TRAFFIC SPIKE ACTIVE</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1.5 rounded-lg font-medium">
              <ShieldCheck className="w-4 h-4" />
              <span>Normal Load</span>
            </div>
          )}

          {/* Connection Status Badge */}
          <div className="flex items-center space-x-2 bg-slate-950/80 border border-slate-800 px-3 py-1.5 rounded-lg">
            <span className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse shadow-sm shadow-emerald-500' : 'bg-red-500'}`} />
            <span className="font-mono text-slate-300">{isConnected ? 'LIVE WS' : 'OFFLINE'}</span>
          </div>

        </div>

      </div>
    </header>
  );
};


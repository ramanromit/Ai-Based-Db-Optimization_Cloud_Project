import React from 'react';
import { ShieldCheck, Activity, Zap, Cpu } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { ShieldCheck, Activity, Zap, Cpu, RefreshCw, AlertTriangle } from 'lucide-react';
import { useStreamStore } from '../store/streamStore';
import { getRetrainStatus, triggerRetrain } from '../api/client';

export const Header: React.FC = () => {
  const { isConnected, isSpikeActive, activeVariant } = useStreamStore();
  const [retrainStatus, setRetrainStatus] = useState<any>(null);
  const [isRetraining, setIsRetraining] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await getRetrainStatus();
        setRetrainStatus(data);
      } catch (e) {
        console.error('Failed to fetch retrain status', e);
      }
    };
    fetchStatus();
    // Poll every 10s
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleRetrain = async (forceBad: boolean) => {
    setIsRetraining(true);
    try {
      await triggerRetrain(forceBad);
      const data = await getRetrainStatus();
      setRetrainStatus(data);
    } catch (e) {
      console.error(e);
      alert('Retrain failed or was rejected. Check explainability logs.');
    } finally {
      setIsRetraining(false);
    }
  };

  const variantLabels = {
    constrained: 'Constrained CAQI (Lagrangian SLA)',
    unconstrained: 'Unconstrained RL (Throughput Only)',
    baseline: 'Aurora Baseline (Criticality-Agnostic)',
    constrained: 'Constrained CAQI',
    unconstrained: 'Unconstrained RL',
    baseline: 'Aurora Baseline',
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
              {retrainStatus?.version && (
                <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider bg-emerald-950 text-emerald-400 border border-emerald-800 rounded">
                  {retrainStatus.version} (LIVE)
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Criticality-Aware Autonomous Query Intelligence for Online Payment Systems
              Autonomous Retraining Loop Active
            </p>
          </div>
        </div>

        {/* Live Controls & Telemetry Badges */}
        <div className="flex items-center space-x-3 text-xs">
          
          {/* Active Allocator Driver */}
          <div className="hidden lg:flex items-center space-x-2">
             <button 
                onClick={() => handleRetrain(false)} 
                disabled={isRetraining}
                className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg border border-slate-700 transition"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRetraining ? 'animate-spin text-cyan-400' : ''}`} />
                <span>{isRetraining ? 'Retraining...' : 'Trigger Retrain'}</span>
              </button>
              <button 
                onClick={() => handleRetrain(true)} 
                disabled={isRetraining}
                className="flex items-center space-x-1 bg-red-950/40 hover:bg-red-900/60 text-red-400 px-3 py-1.5 rounded-lg border border-red-900/50 transition"
                title="Trains a degraded 1-timestep model to demonstrate safety gate rejection."
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Force Reject Demo</span>
              </button>
          </div>

          <div className="hidden lg:flex items-center space-x-2 bg-slate-950/70 border border-slate-800 px-3 py-1.5 rounded-lg">
            <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span className="text-slate-400">Driver:</span>
            <span className="font-semibold text-slate-200 capitalize font-mono">
            <span className="font-semibold text-slate-200 font-mono">
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



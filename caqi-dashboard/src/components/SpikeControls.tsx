import React, { useState, useEffect } from 'react';
import { Zap, RotateCcw, Flame } from 'lucide-react';
import { triggerSpike, clearSpike } from '../api/client';
import { useStreamStore } from '../store/streamStore';
import { useWebSocketStream } from '../hooks/useWebSocketStream';

export const SpikeControls: React.FC = () => {
  const { isSpikeActive } = useStreamStore();
  const { triggerSpikeControl, clearSpikeControl } = useWebSocketStream();
  
  const [activeMultiplier, setActiveMultiplier] = useState<number>(5.0);
  const [countdown, setCountdown] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [customMultiplier, setCustomMultiplier] = useState<number>(5.0);
  const [customDuration, setCustomDuration] = useState<number>(15.0);

  const handleTrigger = async (mult: number, duration: number = customDuration) => {
    setIsLoading(true);
    setActiveMultiplier(mult);
    try {
      await triggerSpike(mult, duration);
      triggerSpikeControl(mult, duration);
      setCountdown(duration);
    } catch (e) {
      console.error('[Trigger Spike Error]:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = async () => {
    setIsLoading(true);
    try {
      await clearSpike();
      clearSpikeControl();
      setCountdown(0);
    } catch (e) {
      console.error('[Clear Spike Error]:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (countdown > 0) {
      const timer = setInterval(() => setCountdown((prev) => prev - 1), 1000);
      return () => clearInterval(timer);
    }
  }, [countdown]);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col justify-between h-full">
      <div>
        <div className="flex items-center space-x-2 mb-2">
          <div className="p-2 bg-red-500/10 rounded-lg text-red-400">
            <Flame className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Live Load Spike Generator</h3>
            <p className="text-xs text-slate-400">Inject traffic bursts to test autonomous SLA enforcement</p>
          </div>
        </div>

        {/* Spike Progress Banner */}
        {isSpikeActive || countdown > 0 ? (
          <div className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center justify-between text-xs text-red-300 animate-pulse">
            <div className="flex items-center space-x-2">
              <Zap className="w-4 h-4 text-red-400 fill-current" />
              <span className="font-semibold">{activeMultiplier}x Traffic Spike Active</span>
            </div>
            <span className="font-mono font-bold text-slate-200">{countdown}s remaining</span>
          </div>
        ) : (
          <div className="mt-3 p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-xs text-slate-400 flex items-center justify-between">
            <span>System operating under normal traffic baseline</span>
            <span className="font-mono text-emerald-400 font-medium">1.0x QPS</span>
          </div>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <label className="text-xs text-slate-400">
          Multiplier
          <input
            type="number"
            min="1"
            max="20"
            step="0.5"
            value={customMultiplier}
            onChange={(event) => setCustomMultiplier(Number(event.target.value))}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-sm font-mono text-slate-200 outline-none focus:border-cyan-500"
          />
        </label>
        <label className="text-xs text-slate-400">
          Duration (seconds)
          <input
            type="number"
            min="1"
            max="300"
            step="1"
            value={customDuration}
            onChange={(event) => setCustomDuration(Number(event.target.value))}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-sm font-mono text-slate-200 outline-none focus:border-cyan-500"
          />
        </label>
        <button
          onClick={() => handleTrigger(customMultiplier, customDuration)}
          disabled={isLoading || customMultiplier < 1 || customMultiplier > 20 || customDuration < 1 || customDuration > 300}
          className="col-span-2 rounded-lg border border-cyan-500/40 bg-cyan-500/10 py-2 text-xs font-semibold text-cyan-300 transition-colors hover:bg-cyan-500/20 disabled:opacity-40"
        >
          Run Custom Spike
        </button>
      </div>

      {/* Trigger Buttons */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        <button
          onClick={() => handleTrigger(3.0)}
          disabled={isLoading}
          className="py-2.5 px-3 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-xl text-xs font-semibold transition-all flex flex-col items-center justify-center space-y-1 hover:border-amber-500/60 disabled:opacity-50"
        >
          <span className="text-sm font-mono font-bold">3x Burst</span>
          <span className="text-[10px] text-amber-400/80">Moderate Load</span>
        </button>

        <button
          onClick={() => handleTrigger(5.0)}
          disabled={isLoading}
          className="py-2.5 px-3 bg-red-500/15 hover:bg-red-500/25 text-red-300 border border-red-500/40 rounded-xl text-xs font-semibold transition-all flex flex-col items-center justify-center space-y-1 hover:border-red-500/70 shadow-lg shadow-red-950/30 disabled:opacity-50"
        >
          <span className="text-sm font-mono font-bold">5x Peak</span>
          <span className="text-[10px] text-red-400/80">Heavy Burst</span>
        </button>

        <button
          onClick={() => handleTrigger(8.0)}
          disabled={isLoading}
          className="py-2.5 px-3 bg-purple-500/15 hover:bg-purple-500/25 text-purple-300 border border-purple-500/40 rounded-xl text-xs font-semibold transition-all flex flex-col items-center justify-center space-y-1 hover:border-purple-500/70 disabled:opacity-50"
        >
          <span className="text-sm font-mono font-bold">8x Extreme</span>
          <span className="text-[10px] text-purple-400/80">Flash Sale</span>
        </button>
      </div>

      {/* Clear Button */}
      <button
        onClick={handleClear}
        disabled={isLoading || (!isSpikeActive && countdown === 0)}
        className="mt-3 w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-xl text-xs font-medium transition-colors flex items-center justify-center space-x-1.5 disabled:opacity-40"
      >
        <RotateCcw className="w-3.5 h-3.5" />
        <span>Reset Load Baseline</span>
      </button>
    </div>
  );
};


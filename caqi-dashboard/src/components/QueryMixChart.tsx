import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { Layers } from 'lucide-react';
import { useStreamStore } from '../store/streamStore';

export const QueryMixChart: React.FC = () => {
  const { recentEvents } = useStreamStore();

  // Aggregate rolling window events into time buckets for smooth stacked area display
  const chartData = React.useMemo(() => {
    if (recentEvents.length === 0) {
      // Clean placeholder structure if empty
      return Array.from({ length: 15 }, (_, i) => ({
        time: `${i}s`,
        AUTH_CRITICAL: 15,
        SETTLEMENT_CRITICAL: 35,
        ANALYTICAL: 50,
      }));
    }

    // Bucket into 15 time slots
    const sliced = recentEvents.slice(0, 45).reverse();
    const buckets: Record<string, { time: string; AUTH_CRITICAL: number; SETTLEMENT_CRITICAL: number; ANALYTICAL: number }> = {};

    sliced.forEach((e, index) => {
      const label = `${index * 2}s`;
      if (!buckets[label]) {
        buckets[label] = { time: label, AUTH_CRITICAL: 0, SETTLEMENT_CRITICAL: 0, ANALYTICAL: 0 };
      }
      if (e.tier in buckets[label]) {
        buckets[label][e.tier] += 1;
      }
    });

    return Object.values(buckets);
  }, [recentEvents]);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-slate-800 rounded-lg text-cyan-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Live Workload Mix Ratio</h3>
            <p className="text-xs text-slate-400">Stacked Query Volume by Criticality Tier (Rolling Window)</p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-4 text-xs font-mono">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
            <span className="text-slate-300">Auth (P0)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
            <span className="text-slate-300">Settlement (P1)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
            <span className="text-slate-300">Analytical (P2)</span>
          </div>
        </div>
      </div>

      <div className="w-full h-64 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorAuth" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f87171" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#f87171" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="colorSettle" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="colorAnalyt" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#c084fc" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#c084fc" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2945" vertical={false} />
            <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
            <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0d1322', borderColor: '#2b395b', borderRadius: '12px', fontSize: '12px' }}
              itemStyle={{ color: '#f8fafc' }}
            />
            <Area type="monotone" dataKey="AUTH_CRITICAL" stackId="1" stroke="#f87171" fill="url(#colorAuth)" />
            <Area type="monotone" dataKey="SETTLEMENT_CRITICAL" stackId="1" stroke="#60a5fa" fill="url(#colorSettle)" />
            <Area type="monotone" dataKey="ANALYTICAL" stackId="1" stroke="#c084fc" fill="url(#colorAnalyt)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};


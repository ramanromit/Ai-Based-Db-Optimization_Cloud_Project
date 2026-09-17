import React, { useState } from 'react';
import { ShieldCheck, ChevronDown, ChevronUp, Server, Lock, Activity, DollarSign, Leaf, Terminal } from 'lucide-react';

export const WellArchitectedPanel: React.FC = () => {
  const [isOpen, setIsOpen] = useState<boolean>(false);

  const pillars = [
    {
      name: 'Operational Excellence',
      icon: Terminal,
      color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
      description: 'Async off-hot-path explainability audit engine emitting human-readable rationales.',
    },
    {
      name: 'Security Posture',
      icon: Lock,
      color: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
      description: 'Structural zero-payload tagging at RDS Proxy level; zero inspection of sensitive raw SQL.',
    },
    {
      name: 'Reliability & Resilience',
      icon: Activity,
      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
      description: 'Constrained Markov Decision Process enforcing hard P(Auth P99 <= 10ms) SLA bound.',
    },
    {
      name: 'Performance Efficiency',
      icon: Server,
      color: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
      description: 'Dynamic dedicated connection pools, read-replica routing, and Redis ElastiCache TTL management.',
    },
    {
      name: 'Cost Optimization',
      icon: DollarSign,
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
      description: 'Selectively degrades analytical query priority under load spikes instead of costly cluster scaling.',
    },
    {
      name: 'Sustainability',
      icon: Leaf,
      color: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/30',
      description: 'Prevents unnecessary compute resource provision over-allocation during temporary traffic bursts.',
    },
  ];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl overflow-hidden transition-all">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              AWS Well-Architected Framework Compliance (6 Pillars)
            </h3>
            <p className="text-xs text-slate-400">Academic Architecture Evaluation Matrix & System Guarantees</p>
          </div>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400">
          <span>{isOpen ? 'Collapse Details' : 'Expand 6 Pillars'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-5 border-t border-slate-800 bg-slate-950/60 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {pillars.map((p, idx) => {
            const Icon = p.icon;
            return (
              <div key={idx} className="p-4 rounded-xl border bg-slate-900/80 border-slate-800/80 space-y-2">
                <div className="flex items-center space-x-2.5">
                  <div className={`p-2 rounded-lg border ${p.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <h4 className="text-xs font-bold text-slate-200">{p.name}</h4>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed font-sans">{p.description}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};


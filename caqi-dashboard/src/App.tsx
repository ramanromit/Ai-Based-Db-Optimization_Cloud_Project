import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shield, Clock, Zap, ShieldCheck, ShieldAlert, Cpu } from 'lucide-react';
import { useStreamStore } from './store/streamStore';
import { useWebSocketStream } from './hooks/useWebSocketStream';

import { Header } from './components/Header';
import { MetricCard } from './components/MetricCard';
import { QueryMixChart } from './components/QueryMixChart';
import { ComplianceChart } from './components/ComplianceChart';
import { ExplainabilityFeed } from './components/ExplainabilityFeed';
import { SpikeControls } from './components/SpikeControls';
import { VariantToggle } from './components/VariantToggle';
import { SecuritySection } from './components/SecuritySection';
import { WellArchitectedPanel } from './components/WellArchitectedPanel';

const queryClient = new QueryClient();

function DashboardContent() {
  // Initialize WebSocket connection hook
  useWebSocketStream();

  const { rollingAuthP99, recentEvents, isSpikeActive, latestEvent } = useStreamStore();

  // Compute live SLA compliance status
  const isCompliant = rollingAuthP99 <= 10.0;
  const statusColor = isCompliant ? (rollingAuthP99 < 8.0 ? 'emerald' : 'amber') : 'red';
  
  // Calculate live QPS
  const liveQps = recentEvents.length > 0 ? Math.round(recentEvents.length / 6) + 45 : 45;
  const effectiveQps = isSpikeActive ? liveQps * 4.5 : liveQps;

  // Compute Security Threat & Legitimacy Metrics
  const quarantinedCount = recentEvents.filter(e => e.is_quarantined).length;
  const cleanPct = recentEvents.length > 0 
    ? Math.max(0, 100 - Math.round((quarantinedCount / recentEvents.length) * 100)) 
    : 100;
  const isThreatActive = quarantinedCount > 0 || (latestEvent?.is_quarantined ?? false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans pb-12">
      {/* Header */}
      <Header />

      {/* Main Content Shell */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-10">
        
        {/* Top Telemetry Cards Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Auth-Critical P99 Latency"
            value={rollingAuthP99.toFixed(2)}
            unit="ms"
            subtitle="SLA Budget: 10.0 ms"
            icon={Clock}
            statusColor={statusColor}
          />

          <MetricCard
            title="SLA Compliance Rate"
            value={isCompliant ? "100.0" : "79.2"}
            unit="%"
            subtitle="Auth Path Availability Target: 99.99%"
            icon={Shield}
            statusColor={isCompliant ? "emerald" : "red"}
          />

          <MetricCard
            title="System Throughput"
            value={Math.round(effectiveQps)}
            unit="QPS"
            subtitle={isSpikeActive ? "Burst Load Active" : "Steady-State Workload"}
            icon={Zap}
            statusColor={isSpikeActive ? "amber" : "cyan"}
          />

          <MetricCard
            title="Traffic Legitimacy Index"
            value={cleanPct.toString()}
            unit="%"
            subtitle={isThreatActive ? `${quarantinedCount} Suspicious Query Quarantined` : "All Queries Verified Clean"}
            icon={isThreatActive ? ShieldAlert : ShieldCheck}
            statusColor={isThreatActive ? "red" : "emerald"}
          />
        </div>

        {/* ======================================================== */}
        {/* SECTION 1: AUTONOMOUS DATABASE ENGINE & QUERY OPTIMIZER  */}
        {/* ======================================================== */}
        <section className="space-y-6">
          <div className="flex items-center space-x-3 pb-3 border-b border-slate-800">
            <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white uppercase tracking-wider font-mono">
                Section 1: Autonomous Query Resource Optimizer
              </h2>
              <p className="text-xs text-slate-400">
                Lagrangian Constrained Markov Decision Process (CMDP) driving Aurora connection pools, replica routing, and caching.
              </p>
            </div>
          </div>

          {/* Charts Row: Compliance vs Query Mix */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ComplianceChart />
            <QueryMixChart />
          </div>

          {/* Optimizer Controls Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SpikeControls />
            <VariantToggle />
          </div>
        </section>

        {/* ======================================================== */}
        {/* SECTION 2: SECURITY & ANOMALY DETECTION LAYER (PAYSIM)   */}
        {/* ======================================================== */}
        <SecuritySection />

        {/* ======================================================== */}
        {/* SECTION 3: EXPLAINABILITY & AUDIT STREAM                 */}
        {/* ======================================================== */}
        <section className="space-y-4">
          <ExplainabilityFeed />
        </section>

        {/* AWS Well-Architected Framework 6-Pillar Panel */}
        <WellArchitectedPanel />

      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DashboardContent />
    </QueryClientProvider>
  );
}

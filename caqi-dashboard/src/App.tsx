import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shield, Clock, Zap, Activity } from 'lucide-react';
import { useStreamStore } from './store/streamStore';
import { useWebSocketStream } from './hooks/useWebSocketStream';

import { Header } from './components/Header';
import { MetricCard } from './components/MetricCard';
import { QueryMixChart } from './components/QueryMixChart';
import { ComplianceChart } from './components/ComplianceChart';
import { ExplainabilityFeed } from './components/ExplainabilityFeed';
import { SpikeControls } from './components/SpikeControls';
import { VariantToggle } from './components/VariantToggle';
import { TransactionInspector } from './components/TransactionInspector';
import { WellArchitectedPanel } from './components/WellArchitectedPanel';

const queryClient = new QueryClient();

function DashboardContent() {
  // Initialize WebSocket connection hook
  useWebSocketStream();

  const { rollingAuthP99, recentEvents, isSpikeActive, activeVariant } = useStreamStore();

  // Compute live SLA compliance status
  const isCompliant = rollingAuthP99 <= 10.0;
  const statusColor = isCompliant ? (rollingAuthP99 < 8.0 ? 'emerald' : 'amber') : 'red';
  
  // Calculate live QPS
  const liveQps = recentEvents.length > 0 ? Math.round(recentEvents.length / 6) + 45 : 45;
  const effectiveQps = isSpikeActive ? liveQps * 4.5 : liveQps;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans pb-12">
      {/* Header */}
      <Header />

      {/* Main Content Shell */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
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
            title="Active Policy Driver"
            value={activeVariant.toUpperCase()}
            unit=""
            subtitle="CMDP Lagrangian Dual Penalty Enabled"
            icon={Activity}
            statusColor="purple"
          />
        </div>

        {/* Middle Charts Row: Headline Compliance vs Live Query Mix */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ComplianceChart />
          <QueryMixChart />
        </div>

        {/* Lower Row: Controls, Inspector, Explainability Feed */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <SpikeControls />
          <VariantToggle />
          <TransactionInspector />
        </div>

        {/* Explainability Audit Feed (Full Width) */}
        <ExplainabilityFeed />

        {/* AWS Well-Architected Framework 6-Pillar Panel (Collapsible Drawer at Bottom) */}
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

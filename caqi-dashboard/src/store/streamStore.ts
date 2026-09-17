import { create } from 'zustand';
import type { QueryProcessedEvent, AllocatorVariant } from '../types/schemas';

interface StreamState {
  isConnected: boolean;
  activeVariant: AllocatorVariant;
  isSpikeActive: boolean;
  recentEvents: QueryProcessedEvent[];
  latestEvent: QueryProcessedEvent | null;
  notifications: string[];
  
  // Rolling metrics for live telemetry cards
  rollingAuthP99: number;
  rollingSettleP99: number;
  rollingAnalytP99: number;

  // Actions
  setConnected: (status: boolean) => void;
  setActiveVariant: (variant: AllocatorVariant) => void;
  setSpikeActive: (active: boolean) => void;
  addEvent: (event: QueryProcessedEvent) => void;
  addNotification: (msg: string) => void;
}

export const useStreamStore = create<StreamState>((set) => ({
  isConnected: false,
  activeVariant: 'constrained',
  isSpikeActive: false,
  recentEvents: [],
  latestEvent: null,
  notifications: [],
  
  rollingAuthP99: 4.4,
  rollingSettleP99: 20.0,
  rollingAnalytP99: 110.0,

  setConnected: (status) => set({ isConnected: status }),
  setActiveVariant: (variant) => set({ activeVariant: variant }),
  setSpikeActive: (active) => set({ isSpikeActive: active }),

  addEvent: (event) =>
    set((state) => {
      const updatedEvents = [event, ...state.recentEvents].slice(0, 100);
      return {
        recentEvents: updatedEvents,
        latestEvent: event,
        activeVariant: event.active_variant,
        isSpikeActive: event.spike_active,
        rollingAuthP99: event.rolling_metrics.auth_p99_ms,
        rollingSettleP99: event.rolling_metrics.settle_p99_ms,
        rollingAnalytP99: event.rolling_metrics.analyt_p99_ms,
      };
    }),

  addNotification: (msg) =>
    set((state) => ({
      notifications: [msg, ...state.notifications].slice(0, 5),
    })),
}));


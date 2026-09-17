import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateCardProps {
  title: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorStateCard: React.FC<ErrorStateCardProps> = ({ title, message, onRetry }) => {
  return (
    <div className="bg-slate-900/80 border border-red-500/30 rounded-xl p-6 flex flex-col items-center justify-center text-center space-y-3">
      <div className="p-3 bg-red-500/10 rounded-full text-red-400">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-slate-200">{title}</h4>
        <p className="text-xs text-slate-400 mt-1">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center space-x-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg transition-colors border border-slate-700"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Connection</span>
        </button>
      )}
    </div>
  );
};


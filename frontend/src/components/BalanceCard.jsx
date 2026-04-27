import React from 'react';
import { useBalance } from '../hooks/useBalance';
import { LoadingSkeleton } from './LoadingSkeleton';

export const BalanceCard = () => {
  const { available_inr, held_inr, total_inr, isLoading, error } = useBalance();

  if (isLoading) return <LoadingSkeleton type="card" />;

  if (error) {
    return (
      <div className="p-6 bg-red-900/20 border border-red-500/50 rounded-xl w-full max-w-sm">
        <h3 className="text-red-400 font-semibold mb-2">Error loading balance</h3>
        <p className="text-sm text-red-300 mb-4">{error.message || 'Network error'}</p>
        <button 
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-red-800 text-white rounded hover:bg-red-700 text-sm font-medium transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gray-900 border border-gray-800 rounded-xl shadow-xl w-full max-w-sm relative overflow-hidden group">
      {/* Decorative gradient blob */}
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl group-hover:bg-emerald-500/20 transition-all duration-500"></div>
      
      <div className="relative z-10">
        <p className="text-sm font-medium text-gray-400 mb-1 tracking-wide uppercase">Available Balance</p>
        <h2 className="text-4xl font-bold text-white mb-6 font-mono tracking-tight drop-shadow-sm">
          <span className="text-emerald-400 mr-1">₹</span>
          {available_inr.replace('₹', '')}
        </h2>
        
        <div className="space-y-3 pt-4 border-t border-gray-800/80">
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-400">Held (in transit)</span>
            <span className="text-amber-400 font-mono font-medium">{held_inr}</span>
          </div>
          <div className="flex justify-between items-center text-sm">
            <span className="text-gray-400">Total</span>
            <span className="text-gray-200 font-mono font-medium">{total_inr}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

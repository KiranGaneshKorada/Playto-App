import { useState } from 'react';
import PropTypes from 'prop-types';
import { useQueryClient } from '@tanstack/react-query';
import { BalanceCard } from '../components/BalanceCard';
import { PayoutForm } from '../components/PayoutForm';
import { PayoutTable } from '../components/PayoutTable';
import { LedgerTable } from '../components/LedgerTable';
import client from '../api/client';
import { format } from 'date-fns';

export const Dashboard = ({ merchant, onLogout }) => {
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const queryClient = useQueryClient();

  const handleReload = () => {
    queryClient.invalidateQueries();
    setLastUpdated(new Date());
  };

  const handleLogout = async () => {
    try {
      await client.post('/api/auth/logout/');
      onLogout();
    } catch (err) {
      console.error('Logout failed', err);
      // Force logout on UI anyway
      onLogout();
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 pb-12">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-emerald-400 to-blue-500 flex items-center justify-center">
              <span className="text-white font-bold text-lg leading-none">P</span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">Playto Payout Engine</h1>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center text-gray-300 font-medium">
                {merchant.merchant_name.charAt(0)}
              </div>
              <span className="text-sm font-medium text-gray-300 hidden sm:block">{merchant.merchant_name}</span>
            </div>
            <button 
              onClick={handleLogout}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        {/* Top Status Bar */}
        <div className="flex justify-between items-end">
          <div>
            <h2 className="text-2xl font-bold text-white">Merchant Overview</h2>
            <p className="text-gray-400 mt-1">Manage your funds and withdrawals securely.</p>
          </div>
          <div className="text-xs text-gray-500 flex items-center gap-2">
            Last updated {format(lastUpdated, 'HH:mm:ss')}
            <button 
              onClick={handleReload}
              className="ml-2 p-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-md transition-colors flex items-center gap-1"
              title="Reload Dashboard"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
              </svg>
              <span>Reload</span>
            </button>
          </div>
        </div>

        {/* Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Left Column (1/3) */}
          <div className="lg:col-span-1 space-y-8">
            <BalanceCard />
            <PayoutForm />
          </div>

          {/* Right Column (2/3) */}
          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-lg font-semibold text-white">Payout History</h3>
            <PayoutTable />
          </div>
          
        </div>

        {/* Bottom Section */}
        <div className="pt-8 space-y-4">
          <h3 className="text-lg font-semibold text-white">Transaction Ledger</h3>
          <LedgerTable />
        </div>

      </main>
    </div>
  );
};

Dashboard.propTypes = {
  merchant: PropTypes.shape({
    merchant_name: PropTypes.string.isRequired,
  }).isRequired,
  onLogout: PropTypes.func.isRequired,
};

import React from 'react';
import { useLedger } from '../hooks/useLedger';
import { LoadingSkeleton } from './LoadingSkeleton';
import { formatDate } from '../utils/format';

export const LedgerTable = () => {
  const { entries, isLoading, error } = useLedger();

  if (isLoading) return <LoadingSkeleton type="table" />;
  if (error) return <div className="p-4 text-red-400 bg-red-900/20 rounded">Failed to load ledger history.</div>;

  if (!entries || entries.length === 0) {
    return (
      <div className="p-8 text-center bg-gray-900/50 rounded-xl border border-gray-800">
        <p className="text-gray-400">No ledger entries found.</p>
      </div>
    );
  }

  return (
    <div className="w-full overflow-hidden rounded-xl border border-gray-800 bg-gray-900 shadow-xl">
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-gray-400 uppercase bg-gray-800/50 border-b border-gray-800">
            <tr>
              <th scope="col" className="px-6 py-4 font-medium tracking-wider">Date</th>
              <th scope="col" className="px-6 py-4 font-medium tracking-wider">Type</th>
              <th scope="col" className="px-6 py-4 font-medium tracking-wider">Description</th>
              <th scope="col" className="px-6 py-4 font-medium tracking-wider text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {entries.map((entry) => {
              const isCredit = entry.entry_type.toLowerCase() === 'credit';
              
              return (
                <tr key={entry.id} className="hover:bg-gray-800/30 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-gray-300">
                    {formatDate(entry.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider ${
                      isCredit ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-800' 
                               : 'bg-rose-900/30 text-rose-400 border border-rose-800'
                    }`}>
                      {entry.entry_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-gray-300 max-w-md truncate">
                    {entry.description}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-right font-mono font-medium ${
                    isCredit ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {isCredit ? '+' : '-'}{entry.amount_inr}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

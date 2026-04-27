import React from 'react';
import { usePayouts } from '../hooks/usePayouts';
import { LoadingSkeleton } from './LoadingSkeleton';
import { StatusBadge } from './StatusBadge';
import { formatDate } from '../utils/format';

export const PayoutTable = () => {
  const { payouts, isLoading, error } = usePayouts();

  if (isLoading) return <LoadingSkeleton type="table" />;
  if (error) return <div className="p-4 text-red-400 bg-red-900/20 rounded">Failed to load payouts.</div>;

  if (!payouts || payouts.length === 0) {
    return (
      <div className="p-8 text-center bg-gray-900/50 rounded-xl border border-gray-800">
        <p className="text-gray-400">No payouts found.</p>
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
              <th scope="col" className="px-6 py-4 font-medium tracking-wider text-right">Amount</th>
              <th scope="col" className="px-6 py-4 font-medium tracking-wider">Bank Account</th>
              <th scope="col" className="px-6 py-4 font-medium tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {payouts.map((payout) => (
              <tr key={payout.id} className="hover:bg-gray-800/30 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-gray-300">
                  <div className="flex flex-col">
                    <span>{formatDate(payout.created_at)}</span>
                    <span className="text-xs text-gray-500 font-mono mt-1" title={payout.id}>
                      {payout.id.split('-')[0]}...
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right font-mono font-medium text-gray-200">
                  {payout.amount_inr}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-gray-300">
                  {payout.bank_account ? (
                    <div className="flex flex-col">
                      <span>{payout.bank_account.bank_name}</span>
                      <span className="text-xs text-gray-500 font-mono">{payout.bank_account.account_number}</span>
                    </div>
                  ) : (
                    <span className="text-gray-500 italic">Unknown</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex flex-col items-start gap-1.5">
                    <StatusBadge state={payout.state} />
                    {payout.attempts > 1 && (
                      <span className="text-[10px] text-gray-500 font-medium px-1.5 py-0.5 bg-gray-800 rounded">
                        {payout.attempts} attempts
                      </span>
                    )}
                    {payout.state === 'failed' && payout.failure_reason && (
                      <span className="text-xs text-red-400/80 max-w-[150px] truncate" title={payout.failure_reason}>
                        {payout.failure_reason}
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

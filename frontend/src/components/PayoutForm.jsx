import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getBankAccounts } from '../api/payouts';
import { useCreatePayout } from '../hooks/useCreatePayout';
import { useBalance } from '../hooks/useBalance';

export const PayoutForm = ({ onSuccess }) => {
  const [amount, setAmount] = useState('');
  const [selectedBank, setSelectedBank] = useState('');
  const [localError, setLocalError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const { available_paise } = useBalance();
  const { data: bankAccounts } = useQuery({
    queryKey: ['bankAccounts'],
    queryFn: getBankAccounts
  });

  const mutation = useCreatePayout();

  // Set default bank account if not selected
  useEffect(() => {
    if (bankAccounts && bankAccounts.length > 0 && !selectedBank) {
      const primary = bankAccounts.find(b => b.is_primary) || bankAccounts[0];
      setSelectedBank(primary.id);
    }
  }, [bankAccounts, selectedBank]);

  const handleSubmit = (e) => {
    e.preventDefault();
    setLocalError(null);
    setSuccessMsg(null);

    // Validate amount
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setLocalError("Please enter a valid amount greater than 0");
      return;
    }

    const amountPaise = Math.round(amountNum * 100);
    
    if (amountPaise > 1000000000) {
      setLocalError("Maximum payout amount is ₹1,00,00,000");
      return;
    }

    if (amountPaise > available_paise) {
      setLocalError("Insufficient available balance");
      return;
    }

    if (!selectedBank) {
      setLocalError("Please select a bank account");
      return;
    }

    mutation.mutate({
      amount_paise: amountPaise,
      bank_account_id: selectedBank
    }, {
      onSuccess: (data) => {
        setSuccessMsg(`Payout requested successfully! ID: ${data.data.id}`);
        setAmount('');
        if (onSuccess) onSuccess(data.data);
      },
      onError: (err) => {
        if (err.response && err.response.data) {
          if (err.response.data.error === 'insufficient_funds') {
            setLocalError("Insufficient available balance (rejected by server)");
          } else {
            setLocalError(err.response.data.error || JSON.stringify(err.response.data));
          }
        } else {
          setLocalError("Network error. You can safely retry.");
        }
      }
    });
  };

  return (
    <div className="p-6 bg-gray-900 border border-gray-800 rounded-xl shadow-lg w-full max-w-md">
      <h3 className="text-xl font-semibold text-white mb-6">Request Payout</h3>
      
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Amount (₹)</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <span className="text-gray-500 font-medium">₹</span>
            </div>
            <input
              type="number"
              step="0.01"
              min="1"
              className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all placeholder-gray-500"
              placeholder="0.00"
              value={amount}
              onChange={(e) => {
                setAmount(e.target.value);
                setLocalError(null);
                setSuccessMsg(null);
              }}
              disabled={mutation.isPending}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Transfer to</label>
          <select
            className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all appearance-none"
            value={selectedBank}
            onChange={(e) => setSelectedBank(e.target.value)}
            disabled={mutation.isPending || !bankAccounts}
          >
            <option value="" disabled>Select a bank account</option>
            {bankAccounts?.map(acc => (
              <option key={acc.id} value={acc.id}>
                {acc.bank_name} ending in {acc.account_number.slice(-4)} {acc.is_primary ? '(Primary)' : ''}
              </option>
            ))}
          </select>
        </div>

        {localError && (
          <div className="p-3 bg-red-900/30 border border-red-800 rounded text-sm text-red-400 flex items-start">
            <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>{localError}</span>
          </div>
        )}

        {successMsg && (
          <div className="p-3 bg-emerald-900/30 border border-emerald-800 rounded text-sm text-emerald-400 flex items-start">
            <svg className="w-5 h-5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
            <span>{successMsg}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={mutation.isPending || !amount || parseFloat(amount) <= 0}
          className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors flex justify-center items-center"
        >
          {mutation.isPending ? (
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : 'Withdraw Funds'}
        </button>
      </form>
    </div>
  );
};

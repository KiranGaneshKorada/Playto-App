import { useQuery } from '@tanstack/react-query';
import { getBalance } from '../api/payouts';

export function useBalance() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['balance'],
    queryFn: getBalance,
  });

  return {
    available_paise: data?.available_balance_paise || 0,
    held_paise: data?.held_balance_paise || 0,
    total_paise: data?.total_balance_paise || 0,
    available_inr: data?.available_balance_inr || '₹0.00',
    held_inr: data?.held_balance_inr || '₹0.00',
    total_inr: data?.total_balance_inr || '₹0.00',
    isLoading,
    error
  };
}

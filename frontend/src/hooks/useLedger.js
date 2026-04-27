import { useQuery } from '@tanstack/react-query';
import { getLedger } from '../api/payouts';

export function useLedger() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ledger'],
    queryFn: getLedger,
  });

  return {
    entries: data || [],
    isLoading,
    error
  };
}

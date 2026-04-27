import { useQuery } from '@tanstack/react-query';
import { getPayouts } from '../api/payouts';

export function usePayouts(stateFilter = '') {
  const { data, isLoading, error } = useQuery({
    queryKey: ['payouts', stateFilter],
    queryFn: () => getPayouts(stateFilter),
  });

  return {
    payouts: data || [],
    isLoading,
    error
  };
}

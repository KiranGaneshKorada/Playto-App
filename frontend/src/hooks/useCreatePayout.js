import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createPayout } from '../api/payouts';
import { v4 as uuidv4 } from 'uuid';

export function useCreatePayout() {
  const queryClient = useQueryClient();
  // Keep the idempotency key in state so retries use the same key
  const [idempotencyKey, setIdempotencyKey] = useState(uuidv4());

  const mutation = useMutation({
    mutationFn: async ({ amount_paise, bank_account_id }) => {
      return await createPayout(amount_paise, bank_account_id, idempotencyKey);
    },
    onSuccess: (data) => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['balance'] });
      queryClient.invalidateQueries({ queryKey: ['payouts'] });
      
      // Check if replayed
      const isReplayed = data.headers && data.headers['x-idempotent-replayed'] === 'true';
      if (!isReplayed) {
        // Generate a new key for the next totally new submission
        setIdempotencyKey(uuidv4());
      }
    },
    onError: (error) => {
      // Don't regenerate idempotency key on error!
      // This ensures if the user hits "retry", we send the exact same key.
      console.error('Failed to create payout', error);
    }
  });

  return mutation;
}

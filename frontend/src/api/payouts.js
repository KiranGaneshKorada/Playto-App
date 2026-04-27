import client from './client';

export const getBalance = async () => {
  const { data } = await client.get('/api/v1/balance/');
  return data;
};

export const getBankAccounts = async () => {
  const { data } = await client.get('/api/v1/bank-accounts/');
  return data;
};

export const createPayout = async (amount_paise, bank_account_id, idempotency_key) => {
  const { data, headers } = await client.post('/api/v1/payouts/', {
    amount_paise,
    bank_account_id
  }, {
    headers: {
      'Idempotency-Key': idempotency_key
    }
  });
  return { data, headers };
};

export const getPayouts = async (state_filter) => {
  let url = '/api/v1/payouts/';
  if (state_filter) {
    url += `?state=${encodeURIComponent(state_filter)}`;
  }
  const { data } = await client.get(url);
  return data;
};

export const getPayout = async (id) => {
  const { data } = await client.get(`/api/v1/payouts/${id}/`);
  return data;
};

export const getLedger = async () => {
  const { data } = await client.get('/api/v1/ledger/');
  return data;
};

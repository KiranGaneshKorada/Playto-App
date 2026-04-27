import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
});

// Hardcoded merchant ID for the demo
export const DEMO_MERCHANT_ID = '8c546f6c-8552-424b-a636-9f1512c35072';

export const getBalance = (merchantId) => api.get(`/merchants/${merchantId}/balance/`);
export const getPayouts = (merchantId) => api.get(`/merchants/${merchantId}/payouts/`);
export const requestPayout = (merchantId, data) => api.post(`/merchants/${merchantId}/payouts/`, data);

export default api;

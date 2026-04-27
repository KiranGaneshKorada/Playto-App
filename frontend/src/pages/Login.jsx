import React, { useState } from 'react';
import client from '../api/client';

export const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      // First ensure we have a CSRF token
      await client.get('/api/auth/csrf/');
      
      const { data } = await client.post('/api/auth/login/', { email, password });
      onLogin(data);
    } catch (err) {
      if (err.response && err.response.data && err.response.data.error) {
        setError(err.response.data.error);
      } else {
        setError('Login failed. Please check your credentials.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 p-4">
      <div className="max-w-md w-full bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl overflow-hidden">
        <div className="p-8">
          <div className="mb-8 text-center">
            <h2 className="text-3xl font-bold text-white mb-2">Playto Payouts</h2>
            <p className="text-gray-400">Sign in to your merchant dashboard</p>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">Email Address</label>
              <input
                type="email"
                required
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                placeholder="merchant@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">Password</label>
              <input
                type="password"
                required
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={loading}
              />
            </div>
            
            {error && (
              <div className="p-3 bg-red-900/30 border border-red-800 rounded text-sm text-red-400 text-center">
                {error}
              </div>
            )}
            
            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white font-medium rounded-lg transition-colors"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

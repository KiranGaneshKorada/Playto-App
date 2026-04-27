import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import client from './api/client';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function AppContent() {
  const [merchant, setMerchant] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check auth session on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const { data } = await client.get('/api/auth/me/');
        setMerchant(data);
      } catch (err) {
        setMerchant(null);
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="animate-pulse flex flex-col items-center">
          <div className="w-12 h-12 bg-gray-800 rounded-full mb-4"></div>
          <div className="h-4 w-32 bg-gray-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (!merchant) {
    return <Login onLogin={(data) => setMerchant(data)} />;
  }

  return <Dashboard merchant={merchant} onLogout={() => setMerchant(null)} />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}

export default App;

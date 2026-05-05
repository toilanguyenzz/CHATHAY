import { useState, useEffect } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function useAuth() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const login = async () => {
    // Simple mock login - no backend call needed for demo
    const mockUser = {
      id: 'zalo_' + Date.now(),
      name: 'User Test',
      isPremium: false,
      coinBalance: 100, // Starting coins for demo
    };
    localStorage.setItem('user', JSON.stringify(mockUser));
    setUser(mockUser);
  };

  const logout = () => {
    localStorage.removeItem('user');
    setUser(null);
  };

  useEffect(() => {
    // Check if user exists in localStorage on mount
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (e) {
        localStorage.removeItem('user');
      }
    }
    setLoading(false);
  }, []);

  return {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
  };
}

'use client';

import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { ConfigProvider, App, theme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { getTheme } from '@/shared/lib/theme';
import { WsProvider } from '@/shared/lib/ws-hooks';
import { GenerationSettingsProvider } from '@/shared/contexts/GenerationSettingsContext';

// ── Theme Context ──────────────────────────────────

type ThemeContextType = {
  isDark: boolean;
  toggle: () => void;
};

const ThemeContext = createContext<ThemeContextType>({ isDark: false, toggle: () => {} });

export const useTheme = () => useContext(ThemeContext);

function getInitialDarkMode(): boolean {
  if (typeof window === 'undefined') return false;
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  return saved === 'dark' || (!saved && prefersDark);
}

function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [isDark, setIsDark] = useState(getInitialDarkMode);

  useEffect(() => {
    document.body.classList.toggle('dark', isDark);
  }, [isDark]);

  const toggle = useCallback(() => {
    setIsDark(prev => {
      const next = !prev;
      localStorage.setItem('theme', next ? 'dark' : 'light');
      document.body.classList.toggle('dark', next);
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ isDark, toggle }}>
      <ConfigProvider
        theme={{
          algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
          token: {
            colorPrimary: '#1677ff',
            colorBgContainer: isDark ? '#1e293b' : '#ffffff',
            colorBgElevated: isDark ? '#1e293b' : '#ffffff',
            colorBgLayout: isDark ? '#0f172a' : '#ffffff',
            colorText: isDark ? '#e2e8f0' : '#1e293b',
            colorBorder: isDark ? '#475569' : '#d9d9d9',
            colorBorderSecondary: isDark ? '#475569' : '#f0f0f0',
            borderRadius: 8,
          },
        }}
      >
        <App>{children}</App>
      </ConfigProvider>
    </ThemeContext.Provider>
  );
}

// ── Auth Context ───────────────────────────────────

type User = {
  id: string;
  role: 'reader' | 'editor' | 'admin';
  username?: string;
  display_name?: string;
  provider: string;
  is_active?: boolean;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  login: () => void;
  logout: () => void;
  establish: (user: User) => void;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
  establish: () => {},
});

export const useAuth = () => useContext(AuthContext);

function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  const savedUser = localStorage.getItem('arkaim_user');
  if (!savedUser) return null;
  try {
    const parsed = JSON.parse(savedUser) as User;
    return parsed?.id ? parsed : null;
  } catch {
    return null;
  }
}

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(getStoredUser);
  const [loading, setLoading] = useState(() => getStoredUser() === null);

  const establish = useCallback((newUser: User) => {
    setUser(newUser);
    try {
      localStorage.setItem('arkaim_user', JSON.stringify(newUser));
    } catch {
      // Не блокируем вход, если storage недоступен (например, приватный режим).
    }
  }, []);

  useEffect(() => {
    const DEV_USER: User = {
      id: 'dev-user-001',
      role: 'admin',
      username: 'developer',
      display_name: 'Разработчик',
      provider: 'dev',
    };

    if (getStoredUser()) {
      return;
    }

    const hasCookie = document.cookie.split(';').some(c => c.trim().startsWith('arkaim_session='));

    const initWithCookie = () => {
      fetch('/auth/me', { credentials: 'same-origin' })
        .then(async (resp) => {
          if (resp.ok) {
            const data = await resp.json();
            if (data.user) {
              setUser(data.user);
              localStorage.setItem('arkaim_user', JSON.stringify(data.user));
              setLoading(false);
              return;
            }
          }
          setUser(DEV_USER);
          setLoading(false);
        })
        .catch(() => { setUser(DEV_USER); setLoading(false); });
    };

    if (hasCookie) {
      initWithCookie();
    } else {
      fetch('/api/auth/dev-login', { method: 'POST' })
        .then(resp => resp.ok ? resp.json() : null)
        .then(data => {
          if (data?.ok && data.user) {
            const u = { ...data.user, provider: data.user.provider || 'dev' };
            setUser(u);
            localStorage.setItem('arkaim_user', JSON.stringify(u));
          } else {
            setUser(DEV_USER);
          }
          setLoading(false);
        })
        .catch(() => { setUser(DEV_USER); setLoading(false); });
    }
  }, []);

  const login = () => { window.location.href = '/login'; };
  const logout = async () => {
    try { await fetch('/api/auth/logout', { method: 'POST' }); } catch {
      // Локальная сессия всё равно должна завершиться даже при недоступном backend.
    }
    localStorage.removeItem('arkaim_user');
    setUser(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, establish }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Query Client ───────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 300_000,
      gcTime: 600_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// ── Root Provider ──────────────────────────────────

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ThemeProvider>
          <WsProvider>
            <GenerationSettingsProvider>
              {children}
            </GenerationSettingsProvider>
          </WsProvider>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
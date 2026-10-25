'use client';

import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { ConfigProvider, App, theme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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

/**
 * Сессия всегда верифицируется против backend на каждом mount.
 *
 * Раньше кэш `localStorage['arkaim_user']` считался доказательством сессии:
 * при наличии кэша `useEffect` выходил досрочно и НЕ проверял `/auth/me`.
 * Cookie `arkaim_session` — HttpOnly с TTL 12ч и из JS не видна, поэтому после
 * её истечения UI оставался «авторизованным» (localStorage), а backend отвечал
 * 401 на все `/book/*` — включая `/book/reader/history`, для которого моков нет.
 *
 * Теперь `loading` остаётся true до вердикта backend, поэтому до готовности
 * сессии экраны и Topbar не рендерятся и запросов «в пустоту» не уходит.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Кэш используем только как мгновенное значение для UI — авторитет остается backend.
  const [user, setUser] = useState<User | null>(getStoredUser);
  const [loading, setLoading] = useState(true);

  const establish = useCallback((newUser: User) => {
    setUser(newUser);
    try {
      localStorage.setItem('arkaim_user', JSON.stringify(newUser));
    } catch {
      // Не блокируем вход, если storage недоступен (например, приватный режим).
    }
  }, []);

  const clearSession = useCallback(() => {
    setUser(null);
    try {
      localStorage.removeItem('arkaim_user');
    } catch {
      // Если storage недоступен — просто сбрасываем состояние в памяти.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const DEV_USER: User = {
      id: 'dev-user-001',
      role: 'admin',
      username: 'developer',
      display_name: 'Разработчик',
      provider: 'dev',
    };

    const finish = (next: User | null) => {
      if (cancelled) return;
      setUser(next);
      setLoading(false);
    };

    (async () => {
      // 1. Реальная cookie-сессия (arkaim_session, HttpOnly — уходит сама).
      let backendReachable = true;
      try {
        const resp = await fetch('/auth/me', { credentials: 'same-origin' });
        if (resp.ok) {
          const data = await resp.json();
          if (data?.user) {
            finish(data.user);
            try { localStorage.setItem('arkaim_user', JSON.stringify(data.user)); } catch { /* ignore */ }
            return;
          }
        }
      } catch {
        // Backend не поднят — dev-фолбэк ниже сохранит работоспособность UI.
        backendReachable = false;
      }

      // 2. Локальная dev-сессия: generate-token → telegram/login ставит cookie.
      try {
        const resp = await fetch('/api/auth/dev-login', { method: 'POST' });
        const data = resp.ok ? await resp.json() : null;
        if (data?.ok && data.user) {
          const u = { ...data.user, provider: data.user.provider || 'dev' };
          if (cancelled) return;
          establish(u);
          setLoading(false);
          return;
        }
      } catch {
        backendReachable = false;
      }

      // 3. Backend жив, но сессию установить не удалось — честно «не авторизован»,
      //    чтобы ProtectedRoute увёл на /login вместо вечных 401.
      if (backendReachable) {
        clearSession();
        setLoading(false);
        return;
      }

      // 4. Backend недоступен — dev-фолбэк (прежнее поведение).
      finish(DEV_USER);
    })();

    return () => { cancelled = true; };
  }, [establish, clearSession]);

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
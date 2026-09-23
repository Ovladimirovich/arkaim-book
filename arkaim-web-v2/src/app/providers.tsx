/**
 * Providers — корневые провайдеры v2 (F1_SPEC).
 * Порядок: Query (server state) → Auth (роль) → Theme → WS (realtime).
 */
'use client';

import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { App as AntApp, ConfigProvider, theme as antdTheme } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/entities/auth/AuthProvider';
import { WsProvider } from '@/shared/realtime/WsProvider';
import { WsToast } from '@/shared/realtime/WsToast';

// ── Theme ──────────────────────────────────────────────
const ThemeContext = createContext<{ isDark: boolean; toggle: () => void }>({ isDark: false, toggle: () => {} });
export const useTheme = () => useContext(ThemeContext);

function ThemeProvider({ children }: { children: ReactNode }) {
  // Ленивая инициализация из localStorage/matchMedia — без setState-в-effect
  const [isDark, setIsDark] = useState<boolean | null>(() => {
    if (typeof window === 'undefined') return null;
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') return true;
    if (saved === 'light') return false;
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const resolvedDark = isDark ?? false;

  const toggle = useCallback(() => {
    setIsDark((prev) => {
      const next = !(prev ?? false);
      localStorage.setItem('theme', next ? 'dark' : 'light');
      return next;
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ isDark: resolvedDark, toggle }}>
      <ConfigProvider
        theme={{
          algorithm: resolvedDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
          token: { colorPrimary: '#1677ff', borderRadius: 8 },
        }}
      >
        <AntApp>{children}</AntApp>
      </ConfigProvider>
    </ThemeContext.Provider>
  );
}

// ── Query client ───────────────────────────────────────
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        gcTime: 300_000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

export function Providers({ children }: { children: ReactNode }) {
  const [qc] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <ThemeProvider>
          <WsProvider>
          <WsToast />
          {children}
        </WsProvider>
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

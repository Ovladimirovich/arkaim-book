/**
 * AuthProvider — единственный источник роли/пользователя (F1_SPEC §8).
 *
 * Отличия от legacy (красные линии):
 *  - /auth/me — единственный источник; 401 = «не залогинен» (никаких моков!);
 *  - dev-вход ТОЛЬКО по флагу NEXT_PUBLIC_DEV_AUTH (никогда автоматически);
 *  - logout вызывает backend POST /auth/logout (снимает cookie).
 *
 * Реализация: server-state через @tanstack/react-query (useQuery /auth/me);
 * контекст только реэкспортирует производное состояние. Никаких
 * setState-в-effect (React Compiler lint).
 */
'use client';

import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getMe, register as apiRegister, telegramLogin as apiTelegramLogin,
  telegramCallback as apiTelegramCallback, devGenerateToken, logout as apiLogout,
  type AuthUser, type RegisterRequest,
} from '@/shared/api/contracts/auth';

export const DEV_AUTH_ENABLED = process.env.NEXT_PUBLIC_DEV_AUTH === '1';

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: () => void;
  logout: () => Promise<void>;
  /** Явный вход (после успешного auth-ответа) — рефетч /auth/me. */
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: () => {},
  logout: async () => {},
  refresh: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const meQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => getMe(),
    staleTime: 5 * 60_000,
    retry: false,
  });

  const user = meQuery.data ?? null;
  const loading = meQuery.isLoading;

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
  }, [queryClient]);

  const login = useCallback(() => {
    router.push('/login');
  }, [router]);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // даже при ошибке сети — локально выходим (cookie мог истечь)
    }
    queryClient.setQueryData(['auth', 'me'], null);
    router.push('/login');
  }, [router, queryClient]);

  const value = useMemo(() => ({ user, loading, login, logout, refresh }), [user, loading, login, logout, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ── Действия входа (используются страницами /login, /register) ──

export async function doRegister(req: RegisterRequest): Promise<AuthUser> {
  const r = await apiRegister(req);
  return r.user;
}

export async function doTelegramCallback(data: Record<string, unknown>): Promise<AuthUser> {
  const r = await apiTelegramCallback(data);
  return r.user;
}

export async function doTelegramTokenLogin(token: string): Promise<AuthUser> {
  const r = await apiTelegramLogin(token);
  return r.user;
}

/** Dev-вход: вызывающий обязан гейтить по DEV_AUTH_ENABLED. */
export async function doDevLogin(username = 'developer'): Promise<AuthUser> {
  if (!DEV_AUTH_ENABLED) {
    throw new Error('dev-вход отключён (NEXT_PUBLIC_DEV_AUTH!=1)');
  }
  const t = await devGenerateToken(username, 'admin');
  const r = await apiTelegramLogin(t.token);
  return r.user;
}

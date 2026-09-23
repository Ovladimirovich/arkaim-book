/**
 * rbac/RoleGate.tsx — ролевая развилка UI (F1_SPEC §8).
 * Единственный способ показать/скрыть контент по роли.
 */
'use client';

import { type ReactNode } from 'react';
import { useAuth } from '@/entities/auth/AuthProvider';
import { can } from './can';

export function RoleGate({
  roles,
  children,
  fallback = null,
}: {
  /** Разрешённые роли (любая из). */
  roles: readonly ('reader' | 'editor' | 'admin')[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { user } = useAuth();
  if (!user) return <>{fallback}</>;
  return <>{roles.includes(user.role) ? children : fallback}</>;
}

/**
 * Проверка доступа к endpoint-действию (по матрице).
 * Используется для кнопок действий, не для навигации.
 */
export function useCan() {
  const { user } = useAuth();
  return (path: string, method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' = 'GET') =>
    user ? can(user.role, path, method) : false;
}

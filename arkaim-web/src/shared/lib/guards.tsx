'use client';

import { useEffect } from 'react';
import { Spin } from 'antd';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/providers';
import type { UserRole } from '@/shared/types';

/**
 * ProtectedRoute — редирект на /login если не авторизован.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) return null;
  return <>{children}</>;
}

/**
 * RoleGuard — показывает контент только если роль пользователя подходит.
 */
export function RoleGuard({
  roles,
  children,
  fallback,
}: {
  roles: UserRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { user, loading } = useAuth();

  if (loading) return <Spin size="small" />;
  if (!user || !roles.includes(user.role)) {
    return fallback ? <>{fallback}</> : null;
  }
  return <>{children}</>;
}

/**
 * (auth)-группа: публичные страницы входа. Без AuthGuard.
 */
'use client';

import { Spin } from 'antd';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/entities/auth/AuthProvider';

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // Уже залогинен — на главную (кроме logout-страниц, которых в v2 нет)
  useEffect(() => {
    if (!loading && user && pathname !== '/login') {
      router.replace('/');
    }
  }, [loading, user, router, pathname]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }
  return <>{children}</>;
}

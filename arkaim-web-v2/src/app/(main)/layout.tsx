/**
 * (main)-группа: защищённые страницы (AuthGuard: без сессии → /login).
 *
 * Reading page (/reading) использует собственный layout (full-height,
 * собственная topbar + TOC) и не обёртывается в AppShell.
 */
'use client';

import { Spin } from 'antd';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/entities/auth/AuthProvider';
import { AppShell } from '@/widgets/app-shell/AppShell';

export default function MainLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  // Reading page has its own layout — skip AppShell
  if (pathname === '/reading') {
    return <>{children}</>;
  }

  return <AppShell>{children}</AppShell>;
}

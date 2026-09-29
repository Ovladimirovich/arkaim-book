'use client';

import { useState } from 'react';
import { Layout, Spin } from 'antd';
import { usePathname } from 'next/navigation';
import { useAuth, useTheme } from '@/app/providers';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useIsMobile } from '@/shared/lib/hooks';

const { Content } = Layout;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { loading } = useAuth();
  const { isDark } = useTheme();
  const pathname = usePathname();
  const isMobile = useIsMobile();
  const [collapsed, setCollapsed] = useState(false);

  if (loading) {
    return (
      <Layout style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </Layout>
    );
  }

  const selectedKey = '/' + (pathname.split('/')[1] || 'book');
  const sidebarWidth = collapsed ? 60 : 220;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sidebar collapsed={collapsed} onCollapse={setCollapsed} selectedKey={selectedKey} />

      <Layout style={{ marginLeft: sidebarWidth, transition: 'margin-left 0.2s' }}>
        <Topbar collapsed={collapsed} onToggleCollapse={() => setCollapsed(!collapsed)} pathname={pathname} />

        <Content style={{ padding: '1.5rem', width: '100%' }}>
          <div style={{ maxWidth: 1100, margin: '0 auto' }}>
            {children}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

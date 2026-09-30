'use client';

import { useEffect, useState } from 'react';
import { Layout, Spin } from 'antd';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/app/providers';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { useIsMobile } from '@/shared/lib/hooks';

const { Content } = Layout;

export function AppShell({ children }: { children: React.ReactNode }) {
  const { loading } = useAuth();
  const pathname = usePathname();
  const isMobile = useIsMobile(1024);
  const [collapsed, setCollapsed] = useState(false);

  // На узком экране сайдбар по умолчанию свёрнут: иначе он отнимал 220px
  // и оставлял контенту слишком мало места.
  useEffect(() => {
    if (isMobile) setCollapsed(true);
  }, [isMobile]);

  if (loading) {
    return (
      <Layout style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </Layout>
    );
  }

  const selectedKey = '/' + (pathname.split('/')[1] || 'book');
  const sidebarWidth = collapsed ? 60 : 220;
  const contentPadding = isMobile ? '1rem 0.75rem' : '1.5rem';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sidebar collapsed={collapsed} onCollapse={setCollapsed} selectedKey={selectedKey} />

      <Layout style={{ marginLeft: sidebarWidth, transition: 'margin-left 0.2s', minWidth: 0 }}>
        <Topbar collapsed={collapsed} onToggleCollapse={() => setCollapsed(!collapsed)} pathname={pathname} />

        <Content style={{ padding: contentPadding, width: '100%' }}>
          <div style={{ maxWidth: 1100, margin: '0 auto' }}>
            {children}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

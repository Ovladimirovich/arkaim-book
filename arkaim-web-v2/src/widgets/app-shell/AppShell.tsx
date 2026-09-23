/**
 * widgets/app-shell — каркас приложения: Topbar + Sidebar (F1_SPEC §1).
 * Навигация — по новому IA от backend-возможностей; доменные пункты F2+
 * отображаются как coming-soon (disabled), отфильтрованы по роли.
 */
'use client';

import { useMemo, useState, type ReactNode } from 'react';
import { Avatar, Badge, Layout, Menu, Tag, Typography } from 'antd';
import { LogoutOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/entities/auth/AuthProvider';
import { useWsStatus } from '@/shared/realtime/WsProvider';
import { navForRole } from '@/shared/rbac/navigation';

const { Sider, Header, Content } = Layout;

const ROLE_COLORS: Record<string, string> = { admin: 'red', editor: 'blue', reader: 'green' };
const ROLE_LABELS: Record<string, string> = { admin: 'Администратор', editor: 'Редактор', reader: 'Читатель' };

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const ws = useWsStatus();
  const pathname = usePathname();

  const groups = useMemo(() => (user ? navForRole(user.role) : []), [user]);

  const menuItems = useMemo(
    () =>
      groups.map((g) => ({
        key: `g:${g.key}`,
        label: g.label,
        children: g.items.map((i) => ({
          key: i.key,
          label: i.comingSoon ? (
            <span style={{ opacity: 0.45 }}>
              {i.label} <Tag style={{ marginLeft: 6 }}>скоро</Tag>
            </span>
          ) : (
            <Link href={i.href ?? '#'}>{i.label}</Link>
          ),
          disabled: i.comingSoon,
        })),
      })),
    [groups],
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} width={220}>
        <div style={{ color: '#fff', padding: '14px 16px', fontWeight: 700, fontSize: 15 }}>
          <ThunderboltOutlined /> {!collapsed && ' Аркаим — v2'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[pathname === '/' ? 'home' : pathname.slice(1)]}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: 16,
            paddingInline: 24,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <Badge
            status={ws.connected ? 'success' : 'default'}
            text={ws.connected ? 'онлайн' : 'нет связи'}
          />
          {user && (
            <>
              <Avatar style={{ background: '#1677ff' }}>
                {(user.display_name ?? user.username ?? user.id).slice(0, 1).toUpperCase()}
              </Avatar>
              <Typography.Text>
                {user.display_name ?? user.username ?? user.id}
                <Tag color={ROLE_COLORS[user.role]} style={{ marginLeft: 8 }}>
                  {ROLE_LABELS[user.role] ?? user.role}
                </Tag>
              </Typography.Text>
              <LogoutOutlined onClick={() => void logout()} style={{ cursor: 'pointer', fontSize: 16 }} />
            </>
          )}
        </Header>
        <Content style={{ padding: 24, maxWidth: 1100, width: '100%', margin: '0 auto' }}>{children}</Content>
      </Layout>
    </Layout>
  );
}

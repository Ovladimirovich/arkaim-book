'use client';

import { useState, useMemo, useEffect, useCallback } from 'react';
import { Button, Space, Typography, Tooltip, Input, Modal, Breadcrumb } from 'antd';
import {
  MenuFoldOutlined, MenuUnfoldOutlined, BulbOutlined, LogoutOutlined,
  SearchOutlined, HomeOutlined,
} from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import { useAuth, useTheme } from '@/app/providers';
import { useWsContext } from '@/shared/lib/ws-hooks';
import { NotificationBell } from '@/shared/ui/NotificationBell';

const { Text } = Typography;

// ── Page Metadata ───────────────────────────────────────────

const PAGE_META: Record<string, { title: string; parent?: string }> = {
  '/book': { title: 'Чат с книгой' },
  '/reading': { title: 'Чтение' },
  '/library': { title: 'Библиотека' },
  '/visual-view': { title: 'Визуал' },
  '/world-explorer': { title: 'Исследование мира' },
  '/map': { title: 'Карта мира' },
  '/profile': { title: 'Профиль', parent: 'Читатель' },
  '/history': { title: 'История', parent: 'Читатель' },
  '/recommendations': { title: 'Рекомендации', parent: 'Читатель' },
  '/notifications': { title: 'Уведомления', parent: 'Читатель' },
  '/interpretations': { title: 'Интерпретации', parent: 'Сообщество' },
  '/artifacts': { title: 'Артефакты', parent: 'Сообщество' },
  '/search': { title: 'Поиск', parent: 'Инструменты' },
  '/editor': { title: 'Редактор', parent: 'Инструменты' },
  '/api': { title: 'API', parent: 'Инструменты' },
  '/settings': { title: 'Настройки', parent: 'Инструменты' },
  '/admin': { title: 'Панель управления', parent: 'Админ' },
  '/xray': { title: 'X-Ray', parent: 'Админ' },
  '/help': { title: 'Справка' },
  '/about': { title: 'О книге' },
};

// ── Search Pages ────────────────────────────────────────────

const SEARCH_PAGES = [
  { path: '/book', title: 'Чат с книгой', group: 'Книга' },
  { path: '/reading', title: 'Чтение', group: 'Книга' },
  { path: '/library', title: 'Библиотека', group: 'Книга' },
  { path: '/visual-view', title: 'Визуал', group: 'Книга' },
  { path: '/assets', title: 'Ассеты', group: 'Книга' },
  { path: '/film-studio', title: 'Film Studio', group: 'Книга' },
  { path: '/world-explorer', title: 'Исследование мира', group: 'Книга' },
  { path: '/map', title: 'Карта мира', group: 'Книга' },
  { path: '/profile', title: 'Профиль', group: 'Читатель' },
  { path: '/history', title: 'История', group: 'Читатель' },
  { path: '/recommendations', title: 'Рекомендации', group: 'Читатель' },
  { path: '/notifications', title: 'Уведомления', group: 'Читатель' },
  { path: '/interpretations', title: 'Интерпретации', group: 'Сообщество' },
  { path: '/artifacts', title: 'Артефакты', group: 'Сообщество' },
  { path: '/search', title: 'Поиск', group: 'Инструменты' },
  { path: '/editor', title: 'Редактор', group: 'Инструменты' },
  { path: '/api', title: 'API', group: 'Инструменты' },
  { path: '/settings', title: 'Настройки', group: 'Инструменты' },
  { path: '/admin', title: 'Панель управления', group: 'Админ' },
  { path: '/xray', title: 'X-Ray', group: 'Админ' },
];

// ── Props ───────────────────────────────────────────────────

type TopbarProps = {
  collapsed: boolean;
  onToggleCollapse: () => void;
  pathname: string;
};

// ── Component ───────────────────────────────────────────────

export function Topbar({ collapsed, onToggleCollapse, pathname }: TopbarProps) {
  const { user, logout } = useAuth();
  const { isDark, toggle } = useTheme();
  const { connected } = useWsContext();
  const router = useRouter();

  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Ctrl+K / Cmd+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
      if (e.key === 'Escape') {
        setSearchOpen(false);
        setSearchQuery('');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const selectedKey = '/' + (pathname.split('/')[1] || 'book');
  const meta = PAGE_META[selectedKey];

  const breadcrumbs = useMemo(() => {
    const items: { title: React.ReactNode }[] = [{ title: <><HomeOutlined /> Наследие</> }];
    if (meta?.parent) {
      items.push({ title: meta.parent });
    }
    if (meta?.title) {
      items.push({ title: meta.title });
    }
    return items;
  }, [meta]);

  const filteredPages = useMemo(() => {
    if (!searchQuery.trim()) return SEARCH_PAGES;
    const q = searchQuery.toLowerCase();
    return SEARCH_PAGES.filter(p =>
      p.title.toLowerCase().includes(q) || p.path.toLowerCase().includes(q)
    );
  }, [searchQuery]);

  return (
    <>
      <div style={{
        height: 48,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        background: 'var(--surface-bg)',
        borderBottom: '1px solid var(--card-border)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}>
        {/* Left: Collapse + Breadcrumbs */}
        <Space size={12}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={onToggleCollapse}
          />
          <Breadcrumb items={breadcrumbs} style={{ fontSize: 13 }} />
        </Space>

        {/* Right: Search + Controls */}
        <Space size={8}>
          <Tooltip title="Поиск (Ctrl+K)">
            <Button
              type="text"
              icon={<SearchOutlined />}
              onClick={() => setSearchOpen(true)}
              style={{ fontSize: 15 }}
            />
          </Tooltip>

          {connected && (
            <Tooltip title="WebSocket подключён">
              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#52c41a' }} />
            </Tooltip>
          )}
          <NotificationBell />
          <Tooltip title={isDark ? 'Светлая тема' : 'Тёмная тема'}>
            <Button type="text" icon={<BulbOutlined />} onClick={toggle} />
          </Tooltip>
          {user && (
            <>
              <Space size={4}>
                <Text type="secondary" style={{ fontSize: '.85rem' }}>
                  {user.display_name || user.username}
                </Text>
                <Text type="secondary" style={{ fontSize: '.75rem' }}>
                  ({user.role})
                </Text>
              </Space>
              <Tooltip title="Выйти">
                <Button type="text" icon={<LogoutOutlined />} onClick={logout} />
              </Tooltip>
            </>
          )}
        </Space>
      </div>

      {/* Search Modal */}
      <Modal
        title="Быстрый переход"
        open={searchOpen}
        onCancel={() => { setSearchOpen(false); setSearchQuery(''); }}
        footer={null}
        width={480}
        styles={{ body: { padding: '12px 0' } }}
      >
        <Input
          prefix={<SearchOutlined />}
          placeholder="Найти страницу..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          autoFocus
          allowClear
          style={{ marginBottom: 12 }}
        />
        <div style={{ maxHeight: 320, overflow: 'auto' }}>
          {filteredPages.length === 0 ? (
            <Text type="secondary" style={{ display: 'block', textAlign: 'center', padding: 24 }}>
              Ничего не найдено
            </Text>
          ) : (
            Object.entries(
              filteredPages.reduce((acc, p) => {
                (acc[p.group] = acc[p.group] || []).push(p);
                return acc;
              }, {} as Record<string, typeof SEARCH_PAGES>)
            ).map(([group, pages]) => (
              <div key={group} style={{ marginBottom: 8 }}>
                <Text type="secondary" style={{ fontSize: 11, fontWeight: 600, display: 'block', padding: '4px 12px' }}>
                  {group}
                </Text>
                {pages.map(p => (
                  <div
                    key={p.path}
                    onClick={() => {
                      router.push(p.path);
                      setSearchOpen(false);
                      setSearchQuery('');
                    }}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      borderRadius: 6,
                      background: pathname === p.path ? 'var(--card-border)' : 'transparent',
                    }}
                    onMouseEnter={e => {
                      if (pathname !== p.path) e.currentTarget.style.background = 'var(--divider-color)';
                    }}
                    onMouseLeave={e => {
                      if (pathname !== p.path) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <Text strong style={{ fontSize: 13 }}>{p.title}</Text>
                    <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>{p.path}</Text>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </Modal>
    </>
  );
}
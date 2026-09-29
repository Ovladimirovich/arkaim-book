'use client';

import { Layout, Menu } from 'antd';
import {
  BookOutlined, ReadOutlined, EditOutlined, VideoCameraOutlined,
  HistoryOutlined, UploadOutlined, PictureOutlined, EyeOutlined,
  TagsOutlined, TrophyOutlined, FileTextOutlined, QuestionCircleOutlined,
  InfoCircleOutlined, SettingOutlined, GlobalOutlined,
  CodeOutlined, DollarOutlined, RiseOutlined, BellOutlined, SearchOutlined, BranchesOutlined,
} from '@ant-design/icons';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/providers';

const { Sider } = Layout;

const NAV_GROUPS = [
  {
    label: 'Книга',
    items: [
      { key: '/ask', icon: <QuestionCircleOutlined />, label: 'Задать вопрос' },
      { key: '/book', icon: <BookOutlined />, label: 'Чат с книгой' },
      { key: '/reading', icon: <FileTextOutlined />, label: 'Чтение' },
      { key: '/screenplay', icon: <VideoCameraOutlined />, label: 'Сценарий' },
      { key: '/library', icon: <ReadOutlined />, label: 'Библиотека' },
      { key: '/genres', icon: <TagsOutlined />, label: 'Жанры' },
      { key: '/visual-view', icon: <EyeOutlined />, label: 'Визуал' },
      { key: '/assets', icon: <PictureOutlined />, label: 'Ассеты' },
      { key: '/film-studio', icon: <VideoCameraOutlined />, label: 'Film Studio' },
      { key: '/world-explorer', icon: <BranchesOutlined />, label: 'Исследование' },
      { key: '/world-engine', icon: <GlobalOutlined />, label: 'World Engine' },
    ],
  },
  {
    label: 'Читатель',
    items: [
      { key: '/profile', icon: <UserOutlined />, label: 'Профиль' },
      { key: '/recommendations', icon: <RiseOutlined />, label: 'Рекомендации' },
      { key: '/history', icon: <HistoryOutlined />, label: 'История' },
      { key: '/notifications', icon: <BellOutlined />, label: 'Уведомления' },
    ],
  },
  {
    label: 'Сообщество',
    items: [
      { key: '/crowdfunding', icon: <DollarOutlined />, label: 'Краудфандинг' },
      { key: '/analytics', icon: <RiseOutlined />, label: 'Аналитика' },
    ],
  },
  {
    label: 'Инструменты',
    items: [
      { key: '/search', icon: <SearchOutlined />, label: 'Поиск' },
      { key: '/editor', icon: <EditOutlined />, label: 'Редактор' },
      { key: '/upload', icon: <UploadOutlined />, label: 'Загрузка' },
      { key: '/visual', icon: <PictureOutlined />, label: 'Визуалы', roles: ['editor', 'admin'] },
      { key: '/api', icon: <CodeOutlined />, label: 'API' },
      { key: '/settings', icon: <SettingOutlined />, label: 'Настройки' },
      { key: '/xray', icon: <EyeOutlined />, label: 'X-Ray', roles: ['admin'] },
      { key: '/admin', icon: <TrophyOutlined />, label: 'Админ', roles: ['admin'] },
    ],
  },
  {
    label: 'Справка',
    items: [
      { key: '/help', icon: <InfoCircleOutlined />, label: 'Инструкции' },
    ],
  },
];

import { UserOutlined } from '@ant-design/icons';

type SidebarProps = {
  collapsed: boolean;
  onCollapse: (collapsed: boolean) => void;
  selectedKey: string;
};

export function Sidebar({ collapsed, onCollapse, selectedKey }: SidebarProps) {
  const { user } = useAuth();
  const router = useRouter();

  const filteredGroups = NAV_GROUPS
    .map(group => ({
      ...group,
      items: group.items.filter(item =>
        !(item as { roles?: string[] }).roles || (item as { roles?: string[] }).roles?.includes(user?.role || '')
      ),
    }))
    .filter(group => group.items.length > 0);

  const menuItems = filteredGroups.flatMap(group => [
    { type: 'group' as const, label: group.label, children: group.items },
  ]);

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onCollapse}
      breakpoint="lg"
      width={220}
      collapsedWidth={60}
      style={{
        background: '#001529',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 100,
        overflow: 'hidden',
      }}
      styles={{ body: { display: 'flex', flexDirection: 'column', overflow: 'hidden' } }}
      trigger={null}
    >
      {/* Logo */}
      <div style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        padding: collapsed ? '0' : '0 16px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        flexShrink: 0,
      }}>
        <Link href="/book" style={{ color: '#fff', fontWeight: 700, fontSize: collapsed ? '1.2rem' : '1rem', textDecoration: 'none', whiteSpace: 'nowrap' }}>
          {collapsed ? '𓃉' : 'Наследие Аркаима'}
        </Link>
      </div>

      {/* Menu — занимает оставшееся место */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          style={{ borderRight: 0 }}
          onClick={({ key }) => router.push(key)}
        />
      </div>
    </Sider>
  );
}




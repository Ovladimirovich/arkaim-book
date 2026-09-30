'use client';

import { Layout, Menu } from 'antd';
import {
  BookOutlined, ReadOutlined, EditOutlined, VideoCameraOutlined,
  HistoryOutlined, UploadOutlined, PictureOutlined, EyeOutlined,
  TagsOutlined, TrophyOutlined, FileTextOutlined, QuestionCircleOutlined,
  InfoCircleOutlined, SettingOutlined, GlobalOutlined,
  CodeOutlined, BellOutlined, SearchOutlined, BranchesOutlined,
  UserOutlined, ClockCircleOutlined, ExperimentOutlined, FundOutlined,
  HomeOutlined, BarChartOutlined, ProfileOutlined, LayoutOutlined,
} from '@ant-design/icons';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/app/providers';

const { Sider } = Layout;

const NAV_GROUPS = [
  {
    label: 'РљРЅРёРіР°',
    items: [
      { key: '/ask', icon: <QuestionCircleOutlined />, label: 'Р—Р°РґР°С‚СЊ РІРѕРїСЂРѕСЃ' },
      { key: '/book', icon: <BookOutlined />, label: 'Р§Р°С‚ СЃ РєРЅРёРіРѕР№' },
      { key: '/reading', icon: <FileTextOutlined />, label: 'Р§С‚РµРЅРёРµ' },
      { key: '/screenplay', icon: <FileTextOutlined />, label: 'РЎС†РµРЅР°СЂРёР№' },
      { key: '/library', icon: <ReadOutlined />, label: 'Р‘РёР±Р»РёРѕС‚РµРєР°' },
      { key: '/genres', icon: <TagsOutlined />, label: 'Р–Р°РЅСЂС‹' },
      { key: '/visual-view', icon: <EyeOutlined />, label: 'Р’РёР·СѓР°Р»' },
      { key: '/assets', icon: <PictureOutlined />, label: 'РђСЃСЃРµС‚С‹' },
      { key: '/film-studio', icon: <VideoCameraOutlined />, label: 'Film Studio' },
      { key: '/world-explorer', icon: <BranchesOutlined />, label: 'РСЃСЃР»РµРґРѕРІР°РЅРёРµ' },
      { key: '/world-engine', icon: <GlobalOutlined />, label: 'World Engine' },
      { key: '/temporal', icon: <ClockCircleOutlined />, label: 'Р’СЂРµРјСЏ РјРёСЂР°' },
      { key: '/map', icon: <GlobalOutlined />, label: 'РљР°СЂС‚Р° РјРёСЂР°' },
      { key: '/story', icon: <ProfileOutlined />, label: 'РСЃС‚РѕСЂРёСЏ РєРЅРёРіРё' },
    ],
  },
  {
    label: 'Р§РёС‚Р°С‚РµР»СЊ',
    items: [
      { key: '/profile', icon: <UserOutlined />, label: 'РџСЂРѕС„РёР»СЊ' },
      { key: '/recommendations', icon: <ReadOutlined />, label: 'Р РµРєРѕРјРµРЅРґР°С†РёРё' },
      { key: '/history', icon: <HistoryOutlined />, label: 'РСЃС‚РѕСЂРёСЏ' },
      { key: '/notifications', icon: <BellOutlined />, label: 'РЈРІРµРґРѕРјР»РµРЅРёСЏ' },
    ],
  },
  {
    label: 'РЎРѕРѕР±С‰РµСЃС‚РІРѕ',
    items: [
      { key: '/crowdfunding', icon: <FundOutlined />, label: 'РљСЂР°СѓРґС„Р°РЅРґРёРЅРі' },
      { key: '/interpretations', icon: <ExperimentOutlined />, label: 'РРЅС‚РµСЂРїСЂРµС‚Р°С†РёРё' },
      { key: '/artifacts', icon: <LayoutOutlined />, label: 'РђСЂС‚РµС„Р°РєС‚С‹' },
      { key: '/analytics', icon: <BarChartOutlined />, label: 'РђРЅР°Р»РёС‚РёРєР°' },
    ],
  },
  {
    label: 'РРЅСЃС‚СЂСѓРјРµРЅС‚С‹',
    items: [
      { key: '/search', icon: <SearchOutlined />, label: 'РџРѕРёСЃРє' },
      { key: '/editor', icon: <EditOutlined />, label: 'Р РµРґР°РєС‚РѕСЂ' },
      { key: '/upload', icon: <UploadOutlined />, label: 'Р—Р°РіСЂСѓР·РєР°' },
      { key: '/visual', icon: <PictureOutlined />, label: 'Р’РёР·СѓР°Р»С‹', roles: ['editor', 'admin'] },
      { key: '/api', icon: <CodeOutlined />, label: 'API' },
      { key: '/settings', icon: <SettingOutlined />, label: 'РќР°СЃС‚СЂРѕР№РєРё' },
      { key: '/xray', icon: <EyeOutlined />, label: 'X-Ray', roles: ['admin'] },
      { key: '/admin', icon: <TrophyOutlined />, label: 'РђРґРјРёРЅ', roles: ['admin'] },
    ],
  },
  {
    label: 'РЎРїСЂР°РІРєР°',
    items: [
      { key: '/help', icon: <InfoCircleOutlined />, label: 'РРЅСЃС‚СЂСѓРєС†РёРё' },
      { key: '/about', icon: <HomeOutlined />, label: 'Рћ РєРЅРёРіРµ' },
    ],
  },
];

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
      {/* Logo вЂ” РІС‹СЃРѕС‚Р° СЃРѕРіР»Р°СЃРѕРІР°РЅР° СЃ Topbar (56px), РёРЅР°С‡Рµ Р±С‹Р»Рё РІРёРґРЅС‹ СЃС‚СѓРїРµРЅСЊРєРё РЅР° СЃС‚С‹РєРµ. */}
      <div style={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'flex-start',
        padding: collapsed ? '0' : '0 16px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        flexShrink: 0,
        overflow: 'hidden',
      }}>
        <Link href="/book" style={{ color: '#fff', fontWeight: 700, fontSize: collapsed ? '1.2rem' : '1rem', textDecoration: 'none', whiteSpace: 'nowrap' }}>
          {collapsed ? 'р“ѓ‰' : 'РќР°СЃР»РµРґРёРµ РђСЂРєР°РёРјР°'}
        </Link>
      </div>

      {/* Menu вЂ” Р·Р°РЅРёРјР°РµС‚ РѕСЃС‚Р°РІС€РµРµСЃСЏ РјРµСЃС‚Рѕ */}
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




/**
 * /help — справка по функционалу приложения (F6).
 * Статическая страница, не требует backend-контрактов.
 */
'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  BookOutlined, MessageOutlined, ReadOutlined, SearchOutlined,
  UserOutlined, TrophyOutlined, HistoryOutlined,
  RiseOutlined, BellOutlined, CodeOutlined, UploadOutlined,
  PictureOutlined, EditOutlined, EyeOutlined, LoginOutlined,
  QuestionCircleOutlined, StarOutlined,
  BulbOutlined, SettingOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Tag, Tabs, Typography, Space } from 'antd';

const { Title, Text, Paragraph } = Typography;

interface HelpPage {
  path: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
  roles: string[];
  color: string;
  category: string;
}

const HELP_PAGES: HelpPage[] = [
  // Книга
  { path: '/ask', icon: <QuestionCircleOutlined />, title: 'Задать вопрос', desc: 'Быстрый вопрос с streaming-ответом. Популярные вопросы на главной.', roles: ['all'], color: '#2563eb', category: 'Книга' },
  { path: '/reading', icon: <ReadOutlined />, title: 'Чтение', desc: 'Режим чтения глав с оглавлением, размером шрифта и навигацией.', roles: ['all'], color: '#2563eb', category: 'Книга' },
  { path: '/library', icon: <BookOutlined />, title: 'Библиотека', desc: 'Геном книги: темы, персонажи, ценности, мир + слои сознания.', roles: ['all'], color: '#2563eb', category: 'Книга' },
  { path: '/world', icon: <EyeOutlined />, title: 'Модель мира', desc: '547 сущностей, 287 связей, 55 форм визуализации.', roles: ['all'], color: '#2563eb', category: 'Книга' },
  { path: '/world-explorer', icon: <SearchOutlined />, title: 'Исследование мира', desc: 'Альтернативные линии развития мира, гипотезы, ветвления.', roles: ['all'], color: '#2563eb', category: 'Книга' },
  { path: '/temporal', icon: <HistoryOutlined />, title: 'Время мира', desc: '12 эпох + Present + экстраполяция будущего.', roles: ['all'], color: '#2563eb', category: 'Книга' },
  { path: '/graph', icon: <TrophyOutlined />, title: 'Граф знаний', desc: 'Визуализация графа связей между сущностями.', roles: ['all'], color: '#2563eb', category: 'Книга' },
  // Читатель
  { path: '/profile', icon: <UserOutlined />, title: 'Профиль', desc: 'Статистика, темы памяти книги, прогресс чтения.', roles: ['all'], color: '#059669', category: 'Читатель' },
  { path: '/history', icon: <HistoryOutlined />, title: 'История', desc: 'Все сессии с фильтрами и поиском по контенту.', roles: ['all'], color: '#059669', category: 'Читатель' },
  { path: '/status', icon: <RiseOutlined />, title: 'Статус системы', desc: 'Health-check, WS-связь, количество контрактов.', roles: ['all'], color: '#059669', category: 'Читатель' },
  // Сообщество
  { path: '/community', icon: <BellOutlined />, title: 'Сообщество', desc: 'Timeline интерпретаций и артефактов читателей.', roles: ['all'], color: '#d97706', category: 'Сообщество' },
  { path: '/proposals/presence', icon: <StarOutlined />, title: 'Presence', desc: 'Предложения о присутствии книги в темах.', roles: ['editor'], color: '#d97706', category: 'Сообщество' },
  { path: '/proposals/email', icon: <MessageOutlined />, title: 'Email-рассылка', desc: 'Черновики email-рассылки по темам.', roles: ['editor'], color: '#d97706', category: 'Сообщество' },
  { path: '/proposals/drafts', icon: <EditOutlined />, title: 'Черновики', desc: 'Управление draft-предложениями.', roles: ['editor'], color: '#d97706', category: 'Сообщество' },
  // Студия
  { path: '/studio', icon: <PictureOutlined />, title: 'Studio', desc: 'Создание сцен, персонажей, локаций + генерация ассетов.', roles: ['editor'], color: '#7c3aed', category: 'Студия' },
  { path: '/upload', icon: <UploadOutlined />, title: 'Загрузка', desc: 'Drag-and-drop загрузка документов в BookOS.', roles: ['editor'], color: '#7c3aed', category: 'Студия' },
  // Админ
  { path: '/admin', icon: <SettingOutlined />, title: 'Админ-панель', desc: 'Пользователи, роли, API-ключи, статистика.', roles: ['admin'], color: '#dc2626', category: 'Админ' },
  { path: '/admin/moderation', icon: <EyeOutlined />, title: 'Модерация', desc: 'Approve/reject интерпретаций и артефактов.', roles: ['admin'], color: '#dc2626', category: 'Админ' },
  { path: '/xray', icon: <RiseOutlined />, title: 'X-Ray', desc: 'Observability: SSE-лента трасировок, статистика.', roles: ['admin'], color: '#dc2626', category: 'Админ' },
  // Auth
  { path: '/login', icon: <LoginOutlined />, title: 'Вход', desc: 'Telegram бот, email, dev-режим.', roles: ['all'], color: '#6b7280', category: 'Авторизация' },
  { path: '/register', icon: <UserOutlined />, title: 'Регистрация', desc: 'Создание аккаунта по email.', roles: ['all'], color: '#6b7280', category: 'Авторизация' },
];

const CATEGORIES = [...new Set(HELP_PAGES.map(p => p.category))];

const STATS = [
  { label: 'Страниц', value: HELP_PAGES.length, icon: <BookOutlined />, color: '#2563eb' },
  { label: 'Категорий', value: CATEGORIES.length, icon: <BulbOutlined />, color: '#7c3aed' },
  { label: 'Backend путей', value: '290', icon: <CodeOutlined />, color: '#059669' },
];

export default function HelpPage() {
  const [activeTab, setActiveTab] = useState('all');

  const tabItems = [
    { key: 'all', label: 'Все страницы' },
    ...CATEGORIES.map(c => ({ key: c, label: c })),
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 0' }}>
      <Title level={2} style={{ marginBottom: 8 }}>
        Справка
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 24 }}>
        Интерактивный справочник по всем страницам и функциям «Наследия Аркаима»
      </Paragraph>

      {/* Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {STATS.map(stat => (
          <Col key={stat.label} xs={24} sm={8}>
            <Card size="small" style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 24, color: stat.color, marginBottom: 4 }}>
                {stat.icon}
              </div>
              <div style={{ fontWeight: 600, fontSize: 20 }}>{stat.value}</div>
              <div style={{ color: '#999', fontSize: 12 }}>{stat.label}</div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems.map(item => ({
          key: item.key,
          label: item.label,
          children: item.key === 'all' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {HELP_PAGES.map(page => (
                <HelpPageCard key={page.path} page={page} />
              ))}
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
              {HELP_PAGES
                .filter(p => p.category === item.key)
                .map(page => (
                  <HelpPageCard key={page.path} page={page} compact />
                ))}
            </div>
          ),
        }))}
      />
    </div>
  );
}

function HelpPageCard({ page, compact }: { page: HelpPage; compact?: boolean }) {
  return (
    <Card
      size="small"
      hoverable
      style={compact ? { borderTop: `3px solid ${page.color}` } : undefined}
      actions={[
        <Link key="link" href={page.path}>
          Перейти →
        </Link>,
      ]}
    >
      <Space>
        <span style={{ fontSize: 18, color: page.color }}>{page.icon}</span>
        <div>
          <div style={{ fontWeight: 500 }}>
            {page.title}
            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
              ({page.path})
            </Text>
          </div>
          <div style={{ fontSize: 13, color: '#666' }}>{page.desc}</div>
          {!compact && (
            <div style={{ marginTop: 4 }}>
              {page.roles.map(r => (
                <Tag key={r} color={r === 'all' ? 'blue' : r === 'editor' ? 'purple' : 'red'} style={{ fontSize: 10 }}>
                  {r}
                </Tag>
              ))}
            </div>
          )}
        </div>
      </Space>
    </Card>
  );
}

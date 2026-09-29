'use client';

import { useState } from 'react';
import { BookOutlined, MessageOutlined, ReadOutlined, SearchOutlined, UserOutlined, TrophyOutlined, HistoryOutlined, DollarOutlined, RiseOutlined, BellOutlined, CodeOutlined, SettingOutlined, UploadOutlined, PictureOutlined, EditOutlined, EyeOutlined, LoginOutlined, QuestionCircleOutlined, ThunderboltOutlined, StarOutlined, BulbOutlined, KeyOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { LCard } from '@/shared/ui/light/LCard';
import { LTag } from '@/shared/ui/light/LTag';
import { LButton } from '@/shared/ui/light/LButton';
import { LAlert } from '@/shared/ui/light/LAlert';

const PAGES = [
  {
    category: 'Книга',
    color: '#2563eb',
    items: [
      { path: '/ask', icon: <QuestionCircleOutlined />, title: 'Задать вопрос', desc: 'Минималистичная страница для быстрого вопроса. Популярные вопросы, streaming ответов.', roles: ['all'] },
      { path: '/book', icon: <MessageOutlined />, title: 'Чат с книгой', desc: 'Полноценный чат с боковой панелью (темы, профиль, статистика). Streaming, сессии, история.', roles: ['all'] },
      { path: '/reading', icon: <ReadOutlined />, title: 'Чтение', desc: 'Режим чтения глав с оглавлением, настройкой размера шрифта и навигацией.', roles: ['all'] },
      { path: '/library', icon: <BookOutlined />, title: 'Библиотека', desc: 'Геном книги (темы, персонажи, ценности, мир) + слои сознания + история эволюции.', roles: ['all'] },
      { path: '/genres', icon: <StarOutlined />, title: 'Жанры', desc: 'Темы по 6 жанровым категориям (мифология, история, философия...) с поиском.', roles: ['all'] },
      { path: '/visual-view', icon: <EyeOutlined />, title: 'Визуал', desc: 'Галерея сцен, персонажей и локаций с подробным просмотром.', roles: ['all'] },
      { path: '/about', icon: <BulbOutlined />, title: 'О книге', desc: 'Геном + слои сознания (знание, смысл, идентичность, миссия) + эволюция.', roles: ['all'] },
      { path: '/search', icon: <SearchOutlined />, title: 'Поиск', desc: '4 вкладки: знания, факты, сущности, граф связей.', roles: ['all'] },
    ],
  },
  {
    category: 'Читатель',
    color: '#059669',
    items: [
      { path: '/profile', icon: <UserOutlined />, title: 'Профиль', desc: 'Быстрые действия, статистика, изученные темы, API-ключи, подписка.', roles: ['all'] },
      { path: '/recommendations', icon: <TrophyOutlined />, title: 'Рекомендации', desc: 'Персонализированные предложения, тренды, прогресс обучения.', roles: ['all'] },
      { path: '/history', icon: <HistoryOutlined />, title: 'История', desc: 'Вопросы, сессии, фильтры по времени.', roles: ['all'] },
      { path: '/settings', icon: <SettingOutlined />, title: 'Настройки', desc: 'Аккаунт, внешний вид, язык, уведомления, безопасность, конфиденциальность.', roles: ['all'] },
    ],
  },
  {
    category: 'Сообщество',
    color: '#d97706',
    items: [
      { path: '/crowdfunding', icon: <DollarOutlined />, title: 'Краудфандинг', desc: 'Кампании, майлстоуны, admin-панель.', roles: ['all'] },
      { path: '/notifications', icon: <BellOutlined />, title: 'Уведомления', desc: 'Предложения Presence, трендовые темы, email-рассылка, подписчики.', roles: ['all'] },
      { path: '/analytics', icon: <RiseOutlined />, title: 'Аналитика', desc: 'Запросы по типу/часам, граф знаний, системная статистика.', roles: ['all'] },
    ],
  },
  {
    category: 'Инструменты',
    color: '#7c3aed',
    items: [
      { path: '/api', icon: <CodeOutlined />, title: 'API', desc: 'Управление ключами, тестер эндпоинтов, примеры кода, документация.', roles: ['all'] },
      { path: '/upload', icon: <UploadOutlined />, title: 'Загрузка', desc: 'Drag-and-drop загрузка документов (.txt, .md, .json, .pdf, .doc).', roles: ['editor', 'admin'] },
      { path: '/visual', icon: <PictureOutlined />, title: 'Визуалы', desc: 'Создание сцен, персонажей, локаций + голосовой ввод.', roles: ['editor', 'admin'] },
      { path: '/editor', icon: <EditOutlined />, title: 'Редактор', desc: 'Создание и редактирование сцен, персонажей и локаций.', roles: ['editor', 'admin'] },
    ],
  },
  {
    category: 'Админ',
    color: '#dc2626',
    items: [
      { path: '/admin', icon: <SettingOutlined />, title: 'Админ-панель', desc: 'Дашборд, пользователи, инвайты, сессии, API-ключи, статистика.', roles: ['admin'] },
      { path: '/xray', icon: <RiseOutlined />, title: 'X-Ray', desc: 'Мониторинг трейсов, диагностика системы.', roles: ['admin'] },
    ],
  },
  {
    category: 'Авторизация',
    color: '#6b7280',
    items: [
      { path: '/login', icon: <LoginOutlined />, title: 'Вход', desc: 'Telegram бот, email, dev-режим.', roles: ['all'] },
      { path: '/register', icon: <UserOutlined />, title: 'Регистрация', desc: 'Создание аккаунта по email.', roles: ['all'] },
    ],
  },
];

const NAV_GROUPS = [
  { title: 'Книга', color: '#2563eb', desc: 'Основные разделы для чтения и взаимодействия с книгой', pages: ['Задать вопрос', 'Чтение', 'Библиотека', 'Жанры', 'Визуал', 'О книге', 'Поиск'] },
  { title: 'Читатель', color: '#059669', desc: 'Персональные данные и настройки', pages: ['Профиль', 'Рекомендации', 'История', 'Настройки'] },
  { title: 'Сообщество', color: '#d97706', desc: 'Краудфандинг, уведомления, аналитика', pages: ['Краудфандинг', 'Уведомления', 'Аналитика'] },
  { title: 'Инструменты', color: '#7c3aed', desc: 'API, загрузка, редактирование контента', pages: ['API', 'Загрузка', 'Визуалы', 'Редактор'] },
  { title: 'Админ', color: '#dc2626', desc: 'Управление системой (только для администраторов)', pages: ['Админ-панель', 'X-Ray'] },
];

const SHORTCUTS = [
  { keys: 'Enter', desc: 'Отправить вопрос в чате' },
  { keys: 'Shift + Enter', desc: 'Новая строка в поле ввода' },
  { keys: 'Клик по теме', desc: 'Быстрый переход к вопросу по теме' },
];

function HelpContent() {
  const [activeTab, setActiveTab] = useState('all');
  const allPages = PAGES.flatMap(p => p.items);

  const tabs = [
    { key: 'all', label: 'Все страницы' },
    ...PAGES.map(cat => ({ key: cat.category, label: cat.category })),
    { key: 'nav', label: 'Навигация' },
    { key: 'shortcuts', label: 'Горячие клавиши' },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ fontSize: 24, fontWeight: 600, marginBottom: 4 }}>Инструкции</h2>
        <p style={{ color: '#999', margin: 0 }}>Справочник по всем страницам и функциям приложения</p>
      </div>

      <LAlert
        message="Добро пожаловать в «Наследие Аркаима»"
        description="Эта страница поможет вам разобраться в функционале. Выберите нужный раздел или воспользуйтесь поиском."
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        <LCard size="small" hoverable>
          <div style={{ textAlign: 'center' }}>
            <BookOutlined style={{ fontSize: 20, color: '#2563eb' }} />
            <div style={{ fontWeight: 600, fontSize: 18 }}>{allPages.length}</div>
            <div style={{ color: '#999', fontSize: 11 }}>страниц</div>
          </div>
        </LCard>
        <LCard size="small" hoverable>
          <div style={{ textAlign: 'center' }}>
            <ThunderboltOutlined style={{ fontSize: 20, color: '#7c3aed' }} />
            <div style={{ fontWeight: 600, fontSize: 18 }}>{PAGES.length}</div>
            <div style={{ color: '#999', fontSize: 11 }}>категорий</div>
          </div>
        </LCard>
        <LCard size="small" hoverable>
          <div style={{ textAlign: 'center' }}>
            <KeyOutlined style={{ fontSize: 20, color: '#059669' }} />
            <div style={{ fontWeight: 600, fontSize: 18 }}>{SHORTCUTS.length}</div>
            <div style={{ color: '#999', fontSize: 11 }}>команд</div>
          </div>
        </LCard>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--divider-color)', marginBottom: 24, overflowX: 'auto' }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: 14,
              color: activeTab === tab.key ? '#1677ff' : '#666',
              borderBottom: activeTab === tab.key ? '2px solid #1677ff' : '2px solid transparent',
              marginBottom: -1,
              fontWeight: activeTab === tab.key ? 500 : 400,
              whiteSpace: 'nowrap',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* All pages */}
      {activeTab === 'all' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {allPages.map(item => (
            <div key={item.path} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 8 }}>
              <span style={{ fontSize: 18, color: '#666' }}>{item.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 500 }}>{item.title} <span style={{ color: '#999', fontSize: 12 }}>({item.path})</span></div>
                <div style={{ fontSize: 13, color: '#666' }}>{item.desc}</div>
                {item.roles[0] !== 'all' && (
                  <div style={{ marginTop: 4, display: 'flex', gap: 4 }}>
                    {item.roles.map(r => <LTag key={r} style={{ fontSize: 10 }}>{r}</LTag>)}
                  </div>
                )}
              </div>
              <Link href={item.path}><LButton size="small" type="link">Перейти →</LButton></Link>
            </div>
          ))}
        </div>
      )}

      {/* Category pages */}
      {PAGES.filter(cat => cat.category === activeTab).map(cat => (
        <div key={cat.category} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {cat.items.map(item => (
            <LCard key={item.path} size="small" hoverable style={{ borderTop: `3px solid ${cat.color}` }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 18, color: cat.color }}>{item.icon}</span>
                  <strong>{item.title}</strong>
                </div>
                <div style={{ fontSize: 12, color: '#999' }}>{item.desc}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                  <code style={{ fontSize: 11, background: 'var(--surface-bg)', padding: '2px 6px', borderRadius: 4 }}>{item.path}</code>
                  <Link href={item.path}><LButton size="small" type="link">Открыть →</LButton></Link>
                </div>
              </div>
            </LCard>
          ))}
        </div>
      ))}

      {/* Navigation */}
      {activeTab === 'nav' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {NAV_GROUPS.map(group => (
            <LCard key={group.title} size="small" title={<span style={{ color: group.color }}>{group.title}</span>}>
              <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>{group.desc}</div>
              {group.pages.map(page => (
                <div key={page} style={{ padding: '2px 0', fontSize: 12 }}>• {page}</div>
              ))}
            </LCard>
          ))}
        </div>
      )}

      {/* Shortcuts */}
      {activeTab === 'shortcuts' && (
        <LCard>
          {SHORTCUTS.map(item => (
            <div key={item.keys} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
              <LTag color="blue" style={{ fontFamily: 'monospace' }}>{item.keys}</LTag>
              <span>{item.desc}</span>
            </div>
          ))}
        </LCard>
      )}
    </div>
  );
}

export default function HelpPage() {
  return <HelpContent />;
}

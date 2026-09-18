/**
 * rbac/navigation.ts — навигационная модель нового IA (FRONTEND_ARCHITECTURE §4.1).
 *
 * Группы/пункты строятся от ВОЗМОЖНОСТЕЙ backend, не от legacy-страниц.
 * F1: доменные пункты — coming-soon (не реализуются, но видимы по роли);
 * реализованные в F1 пункты: только foundation (дашборд, вход/выход).
 *
 * rolesFor — согласовано с фактической матрицей (forensic_rbac2.txt),
 * не со «здравым смыслом».
 */

import type { Role } from '@/shared/api/contracts/auth';

export interface NavItem {
  key: string;
  label: string;
  icon?: string;
  href?: string;
  roles: readonly Role[];
  /** F1: доменные экраны F2+ помечены coming-soon (disabled). */
  comingSoon?: boolean;
  /** Маршрут существует в backend-контракте (для будущего перехода). */
  contractPath?: string;
}

export interface NavGroup {
  key: string;
  label: string;
  roles: readonly Role[];
  items: NavItem[];
}

const E: readonly Role[] = ['editor', 'admin'];
const A: readonly Role[] = ['admin'];
const ALL: readonly Role[] = ['reader', 'editor', 'admin'];

export const NAV_GROUPS: NavGroup[] = [
  {
    key: 'book',
    label: 'Книга',
    roles: ALL,
    items: [
      // F2: активные доменные пункты вертикали «Диалог с книгой».
      { key: 'ask', label: 'Спросить книгу', href: '/', roles: ALL, contractPath: 'POST /book/ask' },
      { key: 'read', label: 'Чтение', href: '/reading', roles: ALL, contractPath: 'GET /book/chapters' },
      { key: 'chat', label: 'Чат с книгой', roles: ALL, comingSoon: true, contractPath: 'POST /v1/stream' },
      { key: 'world', label: 'Модель мира', href: '/world', roles: ALL, contractPath: 'GET /book/world/summary' },
      { key: 'world-explorer', label: 'Исследование мира', href: '/world-explorer', roles: ALL, contractPath: 'POST /book/world-explorer/explore' },
      // F3: вертикаль «Время мира» активна (reader+).
      { key: 'temporal', label: 'Время мира', href: '/temporal', roles: ALL, contractPath: 'GET /book/temporal/chain' },
      { key: 'graph', label: 'Граф знаний', href: '/graph', roles: ALL, contractPath: 'GET /book/graph/stats' },
      { key: 'library', label: 'Геном', href: '/library', roles: ALL, contractPath: 'GET /book/genome' },
      { key: 'analytics', label: 'Аналитика', href: '/analytics', roles: ALL, contractPath: 'GET /book/graph/stats' },
    ],
  },
  {
    key: 'studio',
    label: 'Студия',
    roles: E,
    items: [
      { key: 'studio-main', label: 'Studio', href: '/studio', roles: E },
      { key: 'assets', label: 'Ассеты', roles: E, comingSoon: true, contractPath: 'GET /book/assets' },
      { key: 'film', label: 'Film Studio', roles: E, comingSoon: true, contractPath: 'GET /book/film/list' },
      { key: 'upload', label: 'Загрузка', href: '/upload', roles: E, contractPath: 'POST /book/os/documents/ingest' },
      { key: 'story', label: 'Story Engine', roles: E, comingSoon: true, contractPath: 'POST /book/story-engine/generate' },
    ],
  },
  {
    key: 'proposals',
    label: 'Предложения',
    roles: E,
    items: [
      // F3: Temporal-очередь (M10.2) активна для editor+.
      { key: 'temporal-queue', label: 'Temporal-очередь', href: '/temporal/queue', roles: E, contractPath: 'GET /book/temporal/pending-updates' },
      { key: 'presence', label: 'Presence', roles: E, comingSoon: true, contractPath: 'GET /book/presence/suggestions' },
      { key: 'email', label: 'Email-рассылка', roles: E, comingSoon: true, contractPath: 'GET /book/email/drafts' },
    ],
  },
  {
    key: 'community',
    label: 'Сообщество',
    roles: ALL,
    items: [
      { key: 'interpretations', label: 'Интерпретации', roles: ALL, comingSoon: true, contractPath: 'GET /book/community/interpretations' },
      { key: 'artifacts', label: 'Артефакты', roles: ALL, comingSoon: true, contractPath: 'GET /book/community/artifacts' },
      { key: 'timeline', label: 'Лента', href: '/community', roles: ALL, contractPath: 'GET /book/community/timeline' },
    ],
  },
  {
    key: 'personal',
    label: 'Личное',
    roles: ALL,
    items: [
      // F2: профиль читателя активен; история — часть профиля (topics+last).
      { key: 'profile', label: 'Профиль', href: '/profile', roles: ALL, contractPath: 'GET /book/reader/profile' },
      { key: 'status', label: 'Статус системы', href: '/status', roles: ALL, contractPath: 'GET /health' },
    ],
  },
  {
    key: 'admin',
    label: 'Администрирование',
    roles: A,
    items: [
      { key: 'users', label: 'Пользователи', href: '/admin', roles: A, contractPath: 'GET /auth/admin/users' },
      { key: 'moderation', label: 'Модерация', roles: A, comingSoon: true, contractPath: 'POST /book/community/artifacts/{artifact_id}/approve' },
      { key: 'evolution', label: 'Эволюция', roles: A, comingSoon: true, contractPath: 'GET /book/evolution/versions' },
      { key: 'xray', label: 'X-Ray', roles: A, comingSoon: true, contractPath: 'GET /xray/stats' },
      { key: 'system', label: 'Система', roles: A, comingSoon: true, contractPath: 'GET /book/providers/status' },
    ],
  },
];

/** Видимые группы/пункты для роли. */
export function navForRole(role: Role): NavGroup[] {
  return NAV_GROUPS.filter((g) => g.roles.includes(role)).map((g) => ({
    ...g,
    items: g.items.filter((i) => i.roles.includes(role)),
  }));
}

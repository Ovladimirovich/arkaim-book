import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── Polyfill browser APIs (L-компоненты / иконки / antd-зависимости) ──
beforeAll(() => {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as Record<string, unknown>).ResizeObserver = ResizeObserver;

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});

afterAll(() => {
  delete (globalThis as Record<string, unknown>).ResizeObserver;
});

// ── Mock Next.js navigation / link ──
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// ── Mock auth (ProtectedRoute требует авторизованного пользователя) ──
vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(() => ({ isDark: false, toggle: vi.fn() })),
}));

import { useAuth } from '@/app/providers';
import type { UserRole } from '@/shared/types';
import NotificationsPage from '@/app/notifications/page';
import RecommendationsPage from '@/app/recommendations/page';
import AboutPage from '@/app/about/page';
import AdminPage from '@/app/admin/page';
import MapPage from '@/app/map/page';
import GenresPage from '@/app/genres/page';
import LibraryPage from '@/app/library/page';
import SearchPage from '@/app/search/page';

function mockAuth(role: UserRole = 'reader') {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: '1', role, provider: 'dev', is_active: true, username: 'test', display_name: 'Test User' },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    establish: vi.fn(),
  });
}

// ── fetch mock helpers ──
const fetchMock = vi.fn();

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (key: string) => (key.toLowerCase() === 'content-type' ? 'application/json' : null),
    },
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      // Retry отключён: поведение ошибок должно быть детерминированным в тесте.
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

function expectErrorState(expectedTitle: string) {
  // Вкладки antd Tabs сохраняют открытые подпанели в DOM, поэтому одновременно
  // может быть несколько alert — достаточно, чтобы ожидаемый заголовок среди них.
  return waitFor(
    () => {
      const alerts = screen.getAllByRole('alert');
      expect(alerts.some((a) => (a.textContent ?? '').includes(expectedTitle))).toBe(true);
    },
    { timeout: 3000 },
  );
}

beforeEach(() => {
  mockAuth();
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ─────────────────────────────────────────────────────────────
// Notifications screen: раньше ошибка превращалась в «пустую таблицу».
// ─────────────────────────────────────────────────────────────
describe('Notifications screen — honest error display', () => {
  it('shows error state (not an empty table) on 401', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unauthorized' }, 401)));
    renderWithQuery(<NotificationsPage />);
    await expectErrorState('Не удалось загрузить предложения');
  });

  it('shows error state on 503 (server failure) and on the Trending tab too', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<NotificationsPage />);

    // Вкладка «Предложения» (первая по умолчанию).
    await expectErrorState('Не удалось загрузить предложения');

    // Вкладка «Тренды» — отдельный GET /book/trending, тоже обязан честно показать ошибку.
    fireEvent.click(screen.getByRole('button', { name: /Тренды/ }));
    await expectErrorState('Не удалось загрузить тренды');
  });

  it('shows error state when the server is unreachable (network failure)', async () => {
    fetchMock.mockImplementation(() => Promise.reject(new TypeError('Failed to fetch')));
    renderWithQuery(<NotificationsPage />);
    await expectErrorState('Не удалось загрузить предложения');
  });

  it('recovers after retry once the server returns data', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'down' }, 503)));
    renderWithQuery(<NotificationsPage />);
    await expectErrorState('Не удалось загрузить предложения');

    // Сервер «восстановился».
    fetchMock.mockImplementation(() =>
      Promise.resolve(jsonResponse({ data: [{ id: 's1', topic: 'Тестовая тема', status: 'pending' }] })),
    );
    fireEvent.click(screen.getByRole('button', { name: 'Попробовать снова' }));

    await waitFor(() => expect(screen.getByText('Тестовая тема')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('renders data without an error banner on success', async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(jsonResponse({ data: [{ id: 's1', topic: 'Тестовая тема', status: 'pending' }] })),
    );
    renderWithQuery(<NotificationsPage />);
    await waitFor(() => expect(screen.getByText('Тестовая тема')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────
// Recommendations screen: раньше ошибка превращалась в «вечный спиннер».
// ─────────────────────────────────────────────────────────────
const genomeData = {
  themes: [{ name: 'Аркаим', description: 'Древнее городище' }],
  characters: [],
  values: [],
  world_entities: [],
};

const profileData = {
  topics: [],
  questions_total: 0,
  conversation_count: 0,
  last_topic: '',
};

function successByPath(url: unknown): Response {
  const path = String(url);
  if (path.includes('/book/genome')) return jsonResponse(genomeData);
  if (path.includes('/book/reader/profile')) return jsonResponse(profileData);
  if (path.includes('/presence/trending')) return jsonResponse({ trending: [], total: 0 });
  if (path.includes('/book/trending')) return jsonResponse({ data: [] });
  return jsonResponse({});
}

// Успешные ответы для admin-эндпоинтов: списки — массивы, stats/analytics — объекты.
// Пустые тела {} не подходят: панели делают (data ?? []).filter и падают на объекте.
function adminSuccessByPath(url: unknown): Response {
  const path = String(url);
  if (path.startsWith('/auth/admin/users')) return jsonResponse([]);
  if (path.startsWith('/auth/admin/sessions')) return jsonResponse([]);
  if (path.startsWith('/auth/admin/api-keys')) return jsonResponse([]);
  if (path.startsWith('/auth/admin/invites')) return jsonResponse([]);
  if (path.startsWith('/auth/admin/stats')) return jsonResponse({ users: { total: 3, by_role: {} } });
  if (path.startsWith('/analytics')) return jsonResponse({ total_requests: 10, avg_response_time_ms: 42, error_rate: 1 });
  if (path.startsWith('/book/presence/suggestions')) return jsonResponse({ suggestions: [] });
  if (path.startsWith('/book/community/interpretations')) return jsonResponse({ interpretations: [] });
  if (path.startsWith('/book/community/artifacts')) return jsonResponse({ artifacts: [] });
  return jsonResponse({});
}

// Успешные ответы для экранов map/library/search: реальные формы данных панелей.
// MapView при успехе пытается подгрузить Leaflet (в jsdom <script> так и не
// загружается, колбэк onload не срабатывает — promise висит pending, без
// падения и без alert), поэтому ассерты ведутся на вкладках «Локации»
// и «Хронология», которые Leaflet не требуют.
const mapDataSuccess = {
  regions: [
    {
      id: 'r1',
      name: 'Аркаим',
      type: 'город',
      coordinates: { lat: 52.55, lng: 56.0 },
      description: 'Древнее городище',
      era: 'XIII век',
      color: '#d97706',
      icon: '★',
    },
  ],
  routes: [
    {
      id: 'route1',
      name: 'Путь миграции',
      type: 'route',
      points: [
        { lat: 52, lng: 50 },
        { lat: 52.55, lng: 56.0 },
      ],
      color: '#60a5fa',
      dash: true,
      description: 'Маршрут миграции из книги',
    },
  ],
  energy_lines: [],
};

const temporalNodesSuccess = {
  data: [
    {
      id: 'n1',
      label: 'Основание Аркаима',
      precision: 'century',
      era_id: 'arkaim_era',
      event_ids: [],
      confidence: 0.9,
      is_anchor: true,
      bounds: { start: '1200', end: '1300' },
    },
  ],
};

function mapSuccessByPath(url: unknown): Response {
  const path = String(url);
  if (path.includes('/book/community/map-data')) return jsonResponse(mapDataSuccess);
  if (path.includes('/book/temporal/nodes')) return jsonResponse(temporalNodesSuccess);
  return jsonResponse({});
}

const layersDataSuccess = {
  knowledge_layer: 'Слой знаний',
  meaning_layer: 'Слой смыслов',
  identity_layer: 'Слой идентичности',
  mission_layer: 'Слой миссии',
};

const evolutionDataSuccess = {
  current_version: 'v0.1',
  snapshots: [{ version: 'v0.1', created_at: '2026-01-01T00:00:00Z', description: 'Начальный снимок' }],
};

function librarySuccessByPath(url: unknown): Response {
  const path = String(url);
  if (path.includes('/book/genome')) return jsonResponse(genomeData);
  if (path.includes('/book/layers')) return jsonResponse(layersDataSuccess);
  if (path.includes('/book/evolution/status')) return jsonResponse(evolutionDataSuccess);
  return jsonResponse({});
}

function searchSuccessByPath(url: unknown): Response {
  const path = String(url);
  if (path.includes('/book/os/search')) {
    return jsonResponse({
      results: [{ id: 'k1', text: 'Аркаим — древнее городище', score: 0.9, metadata: { doc_id: '1' } }],
    });
  }
  if (path.includes('/book/community/search')) return jsonResponse({ interpretations: [], artifacts: [], total: 0 });
  if (path.includes('/book/os/facts/search')) {
    return jsonResponse({ facts: [{ id: 'f1', statement: 'Аркаим основан в XIII веке', entity_id: 'region_arkaim', confidence: 0.9 }] });
  }
  if (path.includes('/book/os/entities')) {
    return jsonResponse({ entities: [{ name: 'Аркаим', type: 'городище', resolved: 'region_arkaim' }] });
  }
  if (path.includes('/book/graph/entity/')) {
    return jsonResponse({ neighbors: [{ id: 'n1', name: 'Аркаим', type: 'город', relationship: 'часть' }] });
  }
  return jsonResponse({});
}

describe('Recommendations screen — honest error display', () => {
  it('shows error state (not an endless spinner) on 401', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unauthorized' }, 401)));
    renderWithQuery(<RecommendationsPage />);
    await expectErrorState('Не удалось загрузить рекомендации');
  });

  it('shows error state on 503 (server failure)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<RecommendationsPage />);
    await expectErrorState('Не удалось загрузить рекомендации');
  });

  it('shows error state on the Trending tab when only the trending endpoint fails', async () => {
    // genome/profile отвечают успешно, падает только /book/presence/trending.
    fetchMock.mockImplementation((url: unknown) => {
      const path = String(url);
      if (path.includes('/presence/trending')) return Promise.resolve(jsonResponse({ detail: 'down' }, 503));
      return Promise.resolve(successByPath(url));
    });
    renderWithQuery(<RecommendationsPage />);
    // Ждём, пока genome/profile загрузятся и вкладки станут доступны.
    await waitFor(() => expect(screen.getByRole('button', { name: /Тренды/ })).toBeTruthy(), { timeout: 3000 });
    fireEvent.click(screen.getByRole('button', { name: /Тренды/ }));
    await expectErrorState('Не удалось загрузить тренды');
  });

  it('shows error state when the server is unreachable (network failure)', async () => {
    fetchMock.mockImplementation(() => Promise.reject(new TypeError('Failed to fetch')));
    renderWithQuery(<RecommendationsPage />);
    await expectErrorState('Не удалось загрузить рекомендации');
  });

  it('recovers after retry once the server returns data', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'down' }, 503)));
    renderWithQuery(<RecommendationsPage />);
    await expectErrorState('Не удалось загрузить рекомендации');

    // Сервер «восстановился»: genome и profile отвечают своими данными.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(successByPath(url)));
    fireEvent.click(screen.getByRole('button', { name: 'Попробовать снова' }));

    await waitFor(() => expect(screen.getByText('Рекомендации для вас')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('renders data without an error banner on success', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(successByPath(url)));
    renderWithQuery(<RecommendationsPage />);
    await waitFor(() => expect(screen.getByText('Рекомендации для вас')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
describe('About screen', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.clearAllMocks();
  });

  it('shows an error state when auth rejects (401) with the genome tab active', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unauthorized' }, 401)));
    renderWithQuery(<AboutPage />);
    await expectErrorState('Не удалось загрузить геном книги');
  });

  it('shows StateView when /book/genome returns 503', async () => {
    fetchMock.mockImplementation((url) => jsonResponse({}, url === '/book/genome' ? 503 : 200));
    renderWithQuery(<AboutPage />);
    await expectErrorState('Не удалось загрузить геном книги');
  });

  it('shows StateView on 503 for every tab (genome, layers, evolution)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({}, 503)));
    renderWithQuery(<AboutPage />);
    await expectErrorState('Не удалось загрузить геном книги');
    await fireEvent.click(screen.getByRole('button', { name: /Слои сознания/ }));
    await expectErrorState('Не удалось загрузить слои сознания');
    await fireEvent.click(screen.getByRole('button', { name: /Эволюция/ }));
    await expectErrorState('Не удалось загрузить эволюцию');
  });

  it('shows an error state when the network fails', async () => {
    fetchMock.mockImplementation(() => Promise.reject(new Error('network')));
    renderWithQuery(<AboutPage />);
    await expectErrorState('Не удалось загрузить геном книги');
  });

  it('recovers from an error after retry', async () => {
    // Сначала сервер недоступен: все эндпоинты отвечают 503.
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<AboutPage />);
    await expectErrorState('Не удалось загрузить геном книги');

    // Сервер «восстановился»: геном возвращает реальные данные.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(successByPath(url)));
    const retryBtn = screen.getByRole('button', { name: /Попробовать снова/ });
    await fireEvent.click(retryBtn);

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy(), { timeout: 3000 });
  });

  it('renders data without an error banner on success', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(successByPath(url)));
    renderWithQuery(<AboutPage />);
    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});


describe('Admin screen', () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.clearAllMocks();
    // AdminPage закрыт RoleGuard roles={['admin']}: с ролью 'reader' страница
    // рендерит пустой <div/> — никаких вкладок и alert не будет.
    mockAuth('admin');
  });

  it('shows an error state when auth rejects (401) on the dashboard', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unauthorized' }, 401)));
    renderWithQuery(<AdminPage />);
    await expectErrorState('Не удалось загрузить данные дашборда');
  });

  it('shows StateView on 503 for every dashboard tab', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({}, 503)));
    renderWithQuery(<AdminPage />);
    await expectErrorState('Не удалось загрузить данные дашборда');
    const tabs: Array<{ name: RegExp; expect: string }> = [
      { name: /Дашборд/, expect: 'Не удалось загрузить данные дашборда' },
      { name: /Пользователи/, expect: 'Не удалось загрузить пользователей' },
      { name: /Модерация/, expect: 'Не удалось загрузить интерпретации' },
    ];
    for (const tab of tabs) {
      await fireEvent.click(screen.getByRole('button', { name: tab.name }));
      await expectErrorState(tab.expect);
    }
    // «Артефакты» — подвкладка панели «Модерация» (antd Tabs → role="tab", не button).
    await fireEvent.click(screen.getByRole('tab', { name: /Артефакты/ }));
    await expectErrorState('Не удалось загрузить артефакты');
  });

  it('shows an error state when the network fails', async () => {
    fetchMock.mockImplementation(() => Promise.reject(new Error('network')));
    renderWithQuery(<AdminPage />);
    await expectErrorState('Не удалось загрузить данные дашборда');
  });

  it('recovers from an error after retry', async () => {
    // Сначала сервер недоступен: все admin-эндпоинты отвечают 503.
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<AdminPage />);
    await expectErrorState('Не удалось загрузить данные дашборда');

    // Сервер «восстановился»: эндпоинты отвечают пустыми данными.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(adminSuccessByPath(url)));
    const retryBtn = screen.getByRole('button', { name: /Попробовать снова/ });
    await fireEvent.click(retryBtn);

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 });
    // Блок «Всего запросов» появляется только в успешном состоянии дашборда
    // («Пользователей» встречается и во вкладке, поэтому он не подходит как маркер).
    await waitFor(() => expect(screen.getByText('Всего запросов')).toBeTruthy(), { timeout: 3000 });
  });

  it('renders data without an error banner on success', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(adminSuccessByPath(url)));
    renderWithQuery(<AdminPage />);
    await waitFor(() => expect(screen.getByText('Всего запросов')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('shows StateView (not an empty table) for /auth/admin/users 503', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({}, 503)));
    renderWithQuery(<AdminPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Пользователи/ }));
    await expectErrorState('Не удалось загрузить пользователей');
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('shows StateView for invites / sessions / api-keys panels on 503', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({}, 503)));
    renderWithQuery(<AdminPage />);
    // Заголовки StateView в панелях написаны со строчной («инвайты», «сессии») —
    // ожидания совпадают с текстом панелей, а не с именами вкладок.
    const tabs: Array<{ name: RegExp; expect: string }> = [
      { name: /Инвайты/, expect: 'Не удалось загрузить инвайты' },
      { name: /Сессии/, expect: 'Не удалось загрузить сессии' },
      { name: /API-ключи/, expect: 'Не удалось загрузить API-ключи' },
    ];
    for (const tab of tabs) {
      await fireEvent.click(screen.getByRole('button', { name: tab.name }));
      await expectErrorState(tab.expect);
      expect(screen.queryByRole('table')).toBeNull();
    }
  });

  it('shows StateView on 503 for both moderation panels', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({}, 503)));
    renderWithQuery(<AdminPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Модерация/ }));
    await expectErrorState('Не удалось загрузить интерпретации');
    expect(screen.queryByText('Нет интерпретаций на модерации')).toBeNull();
    // «Артефакты» — подвкладка панели «Модерация» (antd Tabs → role="tab").
    await fireEvent.click(screen.getByRole('tab', { name: /Артефакты/ }));
    await expectErrorState('Не удалось загрузить артефакты');
    expect(screen.queryByText('Нет артефактов на модерации')).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────
// Map screen: при сбое — честная ошибка с повтором, а не пустая карта.
// (Восстановленное покрытие удалённого smoke-скрипта
// make-screens-error-state-smoke; экраны map/genres/search/library
// не имели отдельных тест-файлов.)
// ─────────────────────────────────────────────────────────────
describe('Map screen — honest error display', () => {
  it('shows an error state when auth rejects (401)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unauthorized' }, 401)));
    renderWithQuery(<MapPage />);
    await expectErrorState('Не удалось загрузить карту');
  });

  it('shows StateView on 503 for every tab (map, regions, routes, timeline)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<MapPage />);
    await expectErrorState('Не удалось загрузить карту');
    // «Хронология» — отдельный запрос /book/temporal/nodes: он стартует только
    // при открытии вкладки, поэтому идёт последним.
    const tabs: Array<{ name: RegExp; expect: string }> = [
      { name: /Локации/, expect: 'Не удалось загрузить локации' },
      { name: /Маршруты/, expect: 'Не удалось загрузить маршруты' },
      { name: /Хронология/, expect: 'Не удалось загрузить хронологию' },
    ];
    for (const tab of tabs) {
      await fireEvent.click(screen.getByRole('button', { name: tab.name }));
      await expectErrorState(tab.expect);
    }
  });

  it('shows an error state when the server is unreachable (network failure)', async () => {
    fetchMock.mockImplementation(() => Promise.reject(new TypeError('Failed to fetch')));
    renderWithQuery(<MapPage />);
    await expectErrorState('Не удалось загрузить карту');
  });

  it('shows the chronicle error when only /book/temporal/nodes fails', async () => {
    // map-data отвечает успешно, падает только хроника.
    fetchMock.mockImplementation((url: unknown) => {
      const path = String(url);
      if (path.includes('/book/temporal/nodes')) return Promise.resolve(jsonResponse({ detail: 'down' }, 503));
      return Promise.resolve(mapSuccessByPath(url));
    });
    renderWithQuery(<MapPage />);
    // Карта загрузилась: вкладка «Карта» в jsdom показывает спиннер Leaflet
    // (внешний <script> не загружается) — но без alert.
    await waitFor(() => expect(screen.getByText(/Загрузка карты/)).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
    await fireEvent.click(screen.getByRole('button', { name: /Хронология/ }));
    await expectErrorState('Не удалось загрузить хронологию');
  });

  it('recovers after retry once the server returns data', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<MapPage />);
    await expectErrorState('Не удалось загрузить карту');

    // Сервер «восстановился»: mock переключается ДО клика по повтору.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(mapSuccessByPath(url)));
    await fireEvent.click(screen.getByRole('button', { name: /Попробовать снова/ }));

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 });
    // Вкладка «Локации» показывает регионы без Leaflet.
    await fireEvent.click(screen.getByRole('button', { name: /Локации/ }));
    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('renders data without an error banner on success', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(mapSuccessByPath(url)));
    renderWithQuery(<MapPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Хронология/ }));
    await waitFor(() => expect(screen.getByText('Основание Аркаима')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────
// Genres screen: единый запрос /book/genome, вкладки наследуют его состояние.
// ─────────────────────────────────────────────────────────────
describe('Genres screen — honest error display', () => {
  it('shows an error state when auth rejects (401)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unauthorized' }, 401)));
    renderWithQuery(<GenresPage />);
    await expectErrorState('Не удалось загрузить темы');
  });

  it('shows StateView on 503 for every tab (themes, values, world)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<GenresPage />);
    await expectErrorState('Не удалось загрузить темы');
    const tabs: Array<{ name: RegExp; expect: string }> = [
      { name: /Ценности/, expect: 'Не удалось загрузить ценности' },
      { name: /Мир/, expect: 'Не удалось загрузить мир книги' },
    ];
    for (const tab of tabs) {
      await fireEvent.click(screen.getByRole('button', { name: tab.name }));
      await expectErrorState(tab.expect);
    }
  });

  it('shows an error state when the server is unreachable (network failure)', async () => {
    fetchMock.mockImplementation(() => Promise.reject(new TypeError('Failed to fetch')));
    renderWithQuery(<GenresPage />);
    await expectErrorState('Не удалось загрузить темы');
  });

  it('recovers after retry once the server returns data', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<GenresPage />);
    await expectErrorState('Не удалось загрузить темы');

    // Сервер «восстановился»: mock переключается ДО клика по повтору.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(successByPath(url)));
    await fireEvent.click(screen.getByRole('button', { name: /Попробовать снова/ }));

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy(), { timeout: 3000 });
  });

  it('renders data without an error banner on success', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(successByPath(url)));
    renderWithQuery(<GenresPage />);
    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────
// Library screen: три запроса (genome/layers/evolution), каждая вкладка —
// свой StateView при сбое.
// ─────────────────────────────────────────────────────────────
describe('Library screen — honest error display', () => {
  it('shows an error state when auth rejects (401)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Unauthorized' }, 401)));
    renderWithQuery(<LibraryPage />);
    await expectErrorState('Не удалось загрузить геном книги');
  });

  it('shows StateView on 503 for every tab (genome, layers, evolution)', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<LibraryPage />);
    await expectErrorState('Не удалось загрузить геном книги');
    const tabs: Array<{ name: RegExp; expect: string }> = [
      { name: /Слои сознания/, expect: 'Не удалось загрузить слои сознания' },
      { name: /Эволюция/, expect: 'Не удалось загрузить эволюцию' },
    ];
    for (const tab of tabs) {
      await fireEvent.click(screen.getByRole('button', { name: tab.name }));
      await expectErrorState(tab.expect);
    }
  });

  it('shows an error state when the server is unreachable (network failure)', async () => {
    fetchMock.mockImplementation(() => Promise.reject(new TypeError('Failed to fetch')));
    renderWithQuery(<LibraryPage />);
    await expectErrorState('Не удалось загрузить геном книги');
  });

  it('recovers after retry once the server returns data', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<LibraryPage />);
    await expectErrorState('Не удалось загрузить геном книги');

    // Сервер «восстановился»: mock переключается ДО клика по повтору.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(librarySuccessByPath(url)));
    await fireEvent.click(screen.getByRole('button', { name: /Попробовать снова/ }));

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy(), { timeout: 3000 });
  });

  it('renders data without an error banner on success', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(librarySuccessByPath(url)));
    renderWithQuery(<LibraryPage />);
    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy(), { timeout: 3000 });
    expect(screen.queryByRole('alert')).toBeNull();
  });
});

// ─────────────────────────────────────────────────────────────
// Search screen: запросы стреляются только после ввода строки и нажатия
// «Найти» (enabled: query.length >= 2), поэтому в каждом тесте сначала
// заполняем поле и нажимаем кнопку.
// ─────────────────────────────────────────────────────────────
async function typeAndRunSearch(placeholder: RegExp, value: string) {
  await fireEvent.change(screen.getByPlaceholderText(placeholder), { target: { value } });
  await fireEvent.click(screen.getByRole('button', { name: /Найти/ }));
}

describe('Search screen — honest error display', () => {
  it('shows "Не удалось выполнить поиск" on 503 in the "Везде" tab', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<SearchPage />);
    await typeAndRunSearch(/Поиск по всему/, 'аркаим');
    await expectErrorState('Не удалось выполнить поиск');
  });

  it('recovers after retry in the "Везде" tab once the server returns data', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<SearchPage />);
    await typeAndRunSearch(/Поиск по всему/, 'аркаим');
    await expectErrorState('Не удалось выполнить поиск');

    // Сервер «восстановился»: mock переключается ДО клика по повтору.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(searchSuccessByPath(url)));
    await fireEvent.click(screen.getByRole('button', { name: /Попробовать снова/ }));

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText(/Аркаим — древнее городище/)).toBeTruthy(), { timeout: 3000 });
  });

  it('shows "Не удалось выполнить поиск знаний" on 503 in the "Знания" tab', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<SearchPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Знания/ }));
    await typeAndRunSearch(/Поиск по базе знаний/, 'аркаим');
    await expectErrorState('Не удалось выполнить поиск знаний');
  });

  it('shows "Не удалось выполнить поиск в сообществе" on 503 in the "Сообщество" tab and recovers', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<SearchPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Сообщество/ }));
    await typeAndRunSearch(/Поиск по интерпретациям/, 'аркаим');
    await expectErrorState('Не удалось выполнить поиск в сообществе');

    // Сервер «восстановился»: mock переключается ДО клика по повтору.
    // Ответ пуст — это честное состояние: «Ничего не найдено», а не alert.
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(searchSuccessByPath(url)));
    await fireEvent.click(screen.getByRole('button', { name: /Попробовать снова/ }));

    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull(), { timeout: 3000 });
    await waitFor(() => expect(screen.getByText('Ничего не найдено')).toBeTruthy(), { timeout: 3000 });
  });

  it('shows "Не удалось найти факты" on 503 in the "Факты" tab', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<SearchPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Факты/ }));
    await typeAndRunSearch(/Поиск по фактам/, 'аркаим');
    await expectErrorState('Не удалось найти факты');
  });

  it('shows "Не удалось найти сущности" on 503 in the "Сущности" tab', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<SearchPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Сущности/ }));
    await typeAndRunSearch(/Поиск по сущностям/, 'аркаим');
    await expectErrorState('Не удалось найти сущности');
  });

  it('shows "Не удалось найти связи" on 503 in the "Граф" tab', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({ detail: 'Service Unavailable' }, 503)));
    renderWithQuery(<SearchPage />);
    await fireEvent.click(screen.getByRole('button', { name: /Граф/ }));
    await typeAndRunSearch(/Введите ID сущности/, 'region_arkaim');
    await expectErrorState('Не удалось найти связи');
  });
});



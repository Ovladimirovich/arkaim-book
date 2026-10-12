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
  return waitFor(
    () => {
      const alert = screen.getByRole('alert');
      expect(alert.textContent).toContain(expectedTitle);
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



/**
 * G10 — страница «Визуальные карточки»: единый просмотр 8 карточек слоя.
 *
 * Проверяем:
 *  - карточки отображаются с пометкой «требует подтверждения»;
 *  - показывается промпт-превью (в слое нет готовых изображений);
 *  - поиск фильтрует записи;
 *  - при ошибке API показывается StateView, а не «ничего не найдено».
 */

import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

const getVisualCards = vi.fn();

vi.mock('@/shared/lib/api', () => ({
  api: {
    get: (...args: unknown[]) => getVisualCards(...args),
    post: vi.fn(),
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => '/visual-cards',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));

vi.mock('@/app/providers', () => ({
  useAuth: () => ({
    user: { id: '1', role: 'reader', provider: 'dev', is_active: true, username: 'test', display_name: 'Test User' },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    establish: vi.fn(),
  }),
  useTheme: () => ({ isDark: false, toggle: vi.fn() }),
}));

const SAMPLE = {
  ok: true,
  data: {
    total_files: 8,
    total_entries: 2,
    all_require_author_review: true,
    cards: [
      {
        filename: 'LOCATION_VISUALS.json',
        source_path: 'core/CORE/visual/VISUAL_KNOWLEDGE/LOCATION_VISUALS.json',
        category: 'ARTISTIC_MODEL',
        description: 'Визуальные карточки мест — художественная модель',
        is_canon: false,
        requires_author_review: true,
        intended_use: 'Визуальная форма мест.',
        entry_count: 1,
        entries: [
          {
            group: '',
            key: 'Аркаим',
            fields: { type: 'ancient_settlement', palette: ['#8b5a2b'] },
            prompt_preview: 'ancient_settlement | #8b5a2b',
          },
        ],
      },
      {
        filename: 'STYLE_LIBRARY.json',
        source_path: 'core/CORE/visual/VISUAL_KNOWLEDGE/STYLE_LIBRARY.json',
        category: 'ARTISTIC_MODEL',
        description: 'Стилистические пресеты',
        is_canon: false,
        requires_author_review: true,
        intended_use: 'Стили генерации изображений.',
        entry_count: 1,
        entries: [
          {
            group: '',
            key: 'watercolor',
            fields: { prefix: 'watercolor painting, soft edges' },
            prompt_preview: 'watercolor painting, soft edges',
          },
        ],
      },
    ],
  },
};

beforeAll(() => {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as Record<string, unknown>).ResizeObserver = ResizeObserverMock;

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

async function renderPage() {
  const Page = (await import('@/app/visual-cards/page')).default;
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Page />
    </QueryClientProvider>,
  );
}

describe('G10 — визуальные карточки', () => {
  it('показывает обе карточки с пометкой «требует подтверждения»', async () => {
    getVisualCards.mockResolvedValueOnce(SAMPLE);
    await renderPage();

    await waitFor(() => expect(screen.getByText('LOCATION_VISUALS.json')).toBeTruthy());
    expect(screen.getByText('STYLE_LIBRARY.json')).toBeTruthy();
    expect(screen.getAllByText('требует подтверждения').length).toBe(2);
  });

  it('показывает промпт-превью и предполагаемое использование', async () => {
    getVisualCards.mockResolvedValueOnce(SAMPLE);
    await renderPage();

    await waitFor(() => expect(screen.getByText('ancient_settlement | #8b5a2b')).toBeTruthy());
    expect(screen.getByText(/Визуальная форма мест\./)).toBeTruthy();
    expect(screen.getAllByText(/промпт для генерации изображения/).length).toBe(2);
  });

  it('фильтрует записи по поиску', async () => {
    getVisualCards.mockResolvedValueOnce(SAMPLE);
    await renderPage();

    await waitFor(() => expect(screen.getByText('Аркаим')).toBeTruthy());

    const input = screen.getByPlaceholderText(/Поиск по названию записи/);
    fireEvent.change(input, { target: { value: 'watercolor' } });

    await waitFor(() => expect(screen.queryByText('Аркаим')).toBeNull());
    expect(screen.getByText('watercolor')).toBeTruthy();
  });

  it('показывает ошибку, а не пустой результат, при сбое API', async () => {
    getVisualCards.mockRejectedValueOnce(new Error('boom'));
    await renderPage();

    await waitFor(() => expect(screen.getByText('Не удалось загрузить визуальные карточки')).toBeTruthy());
    expect(screen.getByText(/Сервер ответил ошибкой: boom\./)).toBeTruthy();
  });
});

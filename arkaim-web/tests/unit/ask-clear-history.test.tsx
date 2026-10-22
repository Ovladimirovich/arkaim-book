/**
 * Кнопка «Очистить» на странице «Задать вопрос».
 *
 * Проверяем:
 *  - кнопка вызывает typed-контракт clearReaderSession с текущей сессией;
 *  - после успешной очистки видимая история диалога сбрасывается;
 *  - при ошибке backend показывается текст ошибки, а история не сбрасывается;
 *  - в интерфейсе объяснено, что ИИ работает через RAG-поиск по знаниям книги;
 *  - модалка подтверждения запрашивает явное согласие перед удалением.
 */

import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => '/ask',
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

vi.mock('@/shared/lib/markdown', () => ({
  Markdown: ({ content }: { content: string }) => <div>{content}</div>,
}));

const clearReaderSession = vi.fn();
const getReaderHistoryFull = vi.fn();

vi.mock('@/shared/api/contracts/reader', () => ({
  clearReaderSession: (...args: unknown[]) => clearReaderSession(...args),
  clearReaderHistory: vi.fn(),
  getReaderHistoryFull: (...args: unknown[]) => getReaderHistoryFull(...args),
  recordReaderSessionReference: vi.fn(),
}));

vi.mock('@/shared/lib/api', () => ({
  api: {
    get: vi.fn(() => Promise.resolve({ topics: [], questions_total: 0, last_topic: '' })),
    post: vi.fn(() => Promise.resolve({ data: { answer: '' } })),
  },
}));

import AskPage from '@/app/ask/page';

function renderAsk() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AskPage />
    </QueryClientProvider>,
  );
}

const HISTORY_ITEM = {
  role: 'user',
  content: 'Расскажи про Аркаим',
  created_at: '2026-01-01T10:00:00Z',
};

beforeEach(() => {
  clearReaderSession.mockReset();
  getReaderHistoryFull.mockReset();
  getReaderHistoryFull.mockResolvedValue([HISTORY_ITEM]);
  window.localStorage.clear();
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('Ask: кнопка «Очистить»', () => {
  it('объясняет, что ответы формирует ИИ на основе RAG-поиска по знаниям книги', async () => {
    renderAsk();
    await waitFor(() => expect(getReaderHistoryFull).toHaveBeenCalled());
    expect(screen.getByText(/RAG-поиска по проиндексированным знаниям книги/i)).toBeTruthy();
  });

  it('показывает кнопку «Очистить» и требует подтверждения перед удалением', async () => {
    renderAsk();
    await waitFor(() => expect(getReaderHistoryFull).toHaveBeenCalled());

    const clearButton = await screen.findByRole('button', { name: /Очистить/i });
    fireEvent.click(clearButton);

    // Модалка подтверждения: до нажатия «Очистить» в модалке ничего не удалено.
    expect(screen.getByText('Очистить диалог?')).toBeTruthy();
    expect(screen.getByText(/Знания книги и ваш профиль Читателя не затрагиваются/i)).toBeTruthy();
    expect(clearReaderSession).not.toHaveBeenCalled();

    // Кнопка «Отмена» закрывает модалку и ничего не удаляет.
    fireEvent.click(screen.getByRole('button', { name: /Отмена/i }));
    await waitFor(() => expect(screen.queryByText('Очистить диалог?')).toBeNull());
    expect(clearReaderSession).not.toHaveBeenCalled();
  });

  it('удаляет текущую сессию и сбрасывает видимую историю диалога', async () => {
    clearReaderSession.mockResolvedValue({ deleted: 2, session_id: 'sess-1' });
    window.localStorage.setItem('arkaim_session_id', 'sess-1');

    renderAsk();
    await waitFor(() => expect(getReaderHistoryFull).toHaveBeenCalled());
    await screen.findByText('Расскажи про Аркаим');

    fireEvent.click((await screen.findAllByRole('button', { name: /Очистить/i }))[0]);
    // Сессия, указанная в модалке подтверждения, — та же, что уходит в backend.
    const modalText = screen.getByText(/Будут безвозвратно удалены/i).textContent ?? '';
    const shownSession = modalText.match(/\(([^)]+)\)/)?.[1] ?? '';
    // Кнопка подтверждения в модалке — вторая по порядку.
    fireEvent.click(screen.getAllByRole('button', { name: /Очистить/i })[1]);

    await waitFor(() => expect(clearReaderSession).toHaveBeenCalled());
    // Передаётся текущая сессия страницы (та же, что указана в модалке).
    expect(clearReaderSession.mock.calls[0][0]).toBe(shownSession);
    expect(shownSession.length).toBeGreaterThan(0);
    // Видимая история очищена — прежний вопрос больше не показывается.
    await waitFor(() => expect(screen.queryByText('Расскажи про Аркаим')).toBeNull());
    // Модалка закрылась после успешной очистки.
    await waitFor(() => expect(screen.queryByText('Очистить диалог?')).toBeNull());
  });

  it('показывает ошибку и сохраняет историю, если backend отклонил удаление', async () => {
    clearReaderSession.mockRejectedValue(new Error('HTTP 500'));
    window.localStorage.setItem('arkaim_session_id', 'sess-1');

    renderAsk();
    await waitFor(() => expect(getReaderHistoryFull).toHaveBeenCalled());
    await screen.findByText('Расскажи про Аркаим');

    fireEvent.click((await screen.findAllByRole('button', { name: /Очистить/i }))[0]);
    fireEvent.click(screen.getAllByRole('button', { name: /Очистить/i })[1]);

    await waitFor(() => expect(screen.getByText(/HTTP 500/)).toBeTruthy());
    // История на месте, модалка осталась открытой для повторной попытки.
    expect(screen.getByText('Расскажи про Аркаим')).toBeTruthy();
    expect(screen.getByText('Очистить диалог?')).toBeTruthy();
  });
});

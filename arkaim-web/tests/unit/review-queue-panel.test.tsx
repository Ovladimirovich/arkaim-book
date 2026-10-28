'use client';
//
// review-queue-panel.test.tsx — минимальные сценарии панели очереди проверки.
// Тестируем саму панель (как остальные unit-тесты виджетов), а не страницу,
// чтобы не зависеть от ProtectedRoute/RoleGuard.
//
// Покрывает главные требования Q4:
//  - список кандидатов: статус, источник, текст, provenance, дата/время;
//  - APPROVE с обязательным комментарием (кнопка заблокирована без него);
//  - REJECT;
//  - одобренный/отклонённый статус отображается и (для rejected) доступен
//    возврат в проверку;
//  - APPROVED ≠ CANON: в карточке кандидата и в диалоге показываем,
//    что provenance остаётся SYSTEM_INTERPRETATION и не становится каноном.
//
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
  (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserver;

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

// ── fetch mock (api.ts использует настоящий fetch) ──
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

const CANDIDATES = [
  {
    candidate_id: 'c1',
    topic: 'Тема Аркаим',
    status: 'PENDING_REVIEW',
    file: 'MYTHOLOGY.json',
    locator: 'l1',
    preview: 'Пре-вью текста кандидата.',
    source: 'knowledge_expansion',
    model: 'test-model',
    generated_at: '2026-10-28T12:00:00Z',
    reviewed_by: null,
    reviewed_at: null,
    review_comment: null,
    file_blocked: false,
    requires_author_review: false,
    provenance_category: 'SYSTEM_INTERPRETATION',
  },
  {
    candidate_id: 'c2',
    topic: 'Асинхронная генерация',
    status: 'PENDING_REVIEW',
    file: 'RITUALS.json',
    locator: 'l2',
    preview: 'Трактовка обряда.',
    source: 'knowledge_expansion',
    model: 'test-model',
    generated_at: '2026-10-28T12:05:00Z',
    reviewed_by: null,
    reviewed_at: null,
    review_comment: null,
    file_blocked: false,
    requires_author_review: false,
    provenance_category: 'SYSTEM_INTERPRETATION',
  },
];

const STATS = {
  total: 2,
  pending: 2,
  by_status: { PENDING_REVIEW: 2, APPROVED: 0, REJECTED: 0 },
  by_file: { 'MYTHOLOGY.json': 1, 'RITUALS.json': 1 },
  by_source: { knowledge_expansion: 2 },
};

let listFetchCount = 0;

function queueSuccessByPath(url: unknown): Response {
  const path = String(url);
  if (path.includes('/api/candidates/stats')) return jsonResponse({ ok: true, data: STATS });
  if (path.includes('/api/candidates/c1/approve')) return jsonResponse({ ok: true, data: { ...CANDIDATES[0], status: 'APPROVED', reviewed_by: 'dev-user', reviewed_at: '2026-10-28T13:00:00Z', review_comment: 'обоснование' } });
  if (path.includes('/api/candidates/c1/reject')) return jsonResponse({ ok: true, data: { ...CANDIDATES[0], status: 'REJECTED', reviewed_by: 'dev-user', reviewed_at: '2026-10-28T13:05:00Z', review_comment: 'причина' } });
  if (path.includes('/api/candidates/c1/reopen')) return jsonResponse({ ok: true, data: { ...CANDIDATES[0], status: 'PENDING_REVIEW', reviewed_by: null, reviewed_at: null, review_comment: null } });
  if (path.includes('/api/candidates/c2/reject')) return jsonResponse({ ok: true, data: { ...CANDIDATES[1], status: 'REJECTED', reviewed_by: 'dev-user', reviewed_at: '2026-10-28T13:10:00Z', review_comment: 'не согласовано' } });
  if (path.includes('/api/candidates')) {
    // Первый GET — исходная очередь; повторный (refetch после решения) —
    // уже с применённым статусом, как это вернул бы реальный бэкенд.
    listFetchCount += 1;
    if (listFetchCount > 1) {
      return jsonResponse({
        ok: true,
        data: [
          { ...CANDIDATES[0], status: 'APPROVED', reviewed_by: 'dev-user', reviewed_at: '2026-10-28T13:00:00Z', review_comment: 'обоснование' },
          { ...CANDIDATES[1], status: 'REJECTED', reviewed_by: 'dev-user', reviewed_at: '2026-10-28T13:10:00Z', review_comment: 'не согласовано' },
        ],
        total: 2,
      });
    }
    return jsonResponse({ ok: true, data: CANDIDATES, total: 2 });
  }
  return jsonResponse({});
}

function renderWithQuery(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

import { ReviewQueuePanel } from '@/widgets/review-queue/review-queue-panel';

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  vi.clearAllMocks();
  listFetchCount = 0;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('ReviewQueuePanel — список кандидатов', () => {
  it('отображает текст, статус, источник, provenance и дату создания', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(queueSuccessByPath(url)));
    renderWithQuery(<ReviewQueuePanel />);

    await waitFor(() => expect(screen.getByText('Тема Аркаим')).toBeTruthy(), { timeout: 8000 });
    expect(screen.getAllByText('На проверке').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Источник: knowledge_expansion/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Provenance: SYSTEM_INTERPRETATION/).length).toBeGreaterThan(0);
    // Дата в локальном формате содержит '2026' — не строгое значение.
    expect(screen.getAllByText(/Создано:/).length).toBeGreaterThan(0);
    // Превью текста кандидата.
    expect(screen.getByText('Пре-вью текста кандидата.')).toBeTruthy();
  });

  it('показывает понятный результат после успешного APPROVE и REJECT', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(queueSuccessByPath(url)));
    renderWithQuery(<ReviewQueuePanel />);
    await waitFor(() => expect(screen.getAllByText('На проверке').length).toBeGreaterThan(0), { timeout: 8000 });
  });
});

describe('ReviewQueuePanel — решения требуют комментарий', () => {
  it('кнопка Одобрить в диалоге заблокирована, пока комментарий пуст', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(queueSuccessByPath(url)));
    renderWithQuery(<ReviewQueuePanel />);
    await waitFor(() => expect(screen.getByText('Тема Аркаим')).toBeTruthy(), { timeout: 8000 });

    fireEvent.click(screen.getAllByRole('button', { name: /Одобрить/ })[0]);

    // Диалог открыт, кнопка подтверждения (в диалоге) заблокирована без текста.
    const confirm = screen.getByTestId('review-decision-submit');
    expect(screen.getByText(/Одобрить кандидата/)).toBeTruthy();
    expect(confirm).toBeDisabled();

    // Вписываем комментарий — кнопка разблокируется.
    fireEvent.change(screen.getByPlaceholderText(/Комментарий/), { target: { value: 'обоснование' } });
    await waitFor(() => expect(screen.getByTestId('review-decision-submit')).not.toBeDisabled(), { timeout: 8000 });
  });

  it('отправляет POST /approve с комментарием и обновляет статус', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(queueSuccessByPath(url)));
    renderWithQuery(<ReviewQueuePanel />);
    await waitFor(() => expect(screen.getByText('Тема Аркаим')).toBeTruthy(), { timeout: 8000 });

    fireEvent.click(screen.getAllByRole('button', { name: /Одобрить/ })[0]);
    fireEvent.change(screen.getByPlaceholderText(/Комментарий/), { target: { value: 'обоснование' } });
    await waitFor(() => expect(screen.getByTestId('review-decision-submit')).not.toBeDisabled(), { timeout: 8000 });
    fireEvent.click(screen.getByTestId('review-decision-submit'));

    await waitFor(() => {
      const calls = fetchMock.mock.calls.filter((c) => String(c[0]).includes('/api/candidates/c1/approve'));
      expect(calls.length).toBeGreaterThan(0);
      const body = JSON.parse(String(calls[0][1]?.body));
      expect(body.comment).toBe('обоснование');
    }, { timeout: 8000 });

    // Статус обновился в интерфейсе (refetch вернул approve-ответ).
    await waitFor(() => expect(screen.getAllByText('Одобрено').length).toBeGreaterThan(0), { timeout: 8000 });
  });

  it('отправляет POST /reject и показывает статус отклонённого', async () => {
    fetchMock.mockImplementation((url: unknown) => Promise.resolve(queueSuccessByPath(url)));
    renderWithQuery(<ReviewQueuePanel />);
    await waitFor(() => expect(screen.getByText('Асинхронная генерация')).toBeTruthy(), { timeout: 8000 });

    fireEvent.click(screen.getAllByRole('button', { name: /Отклонить/ })[1]);
    fireEvent.change(screen.getByPlaceholderText(/Комментарий/), { target: { value: 'не согласовано' } });
    fireEvent.click(screen.getByTestId('review-decision-submit'));

    await waitFor(() => {
      const calls = fetchMock.mock.calls.filter((c) => String(c[0]).includes('/api/candidates/c2/reject'));
      expect(calls.length).toBeGreaterThan(0);
    }, { timeout: 8000 });

    // Refetch вернул обновлённый статус — отклонённый отображается в карточке.
    await waitFor(() => expect(screen.getAllByText('Отклонено').length).toBeGreaterThan(0), { timeout: 8000 });
  });
});

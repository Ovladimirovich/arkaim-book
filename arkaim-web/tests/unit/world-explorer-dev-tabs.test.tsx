/**
 * Q4 (OWNER-GO): dev-панели /world-explorer — только editor/admin.
 *
 * Вкладки «Поиск в источниках» и «Кэш» и автозагрузка /cache/stats
 * видны только пользователям с ролью editor/admin. Для reader
 * страница открывается как раньше, но без dev-секций.
 */
import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest';
import React from 'react';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

beforeAll(() => {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserver;

  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      matches: false,
      media: '',
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

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/world-explorer',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
}));

vi.mock('@/shared/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/shared/lib/ws-hooks', () => ({
  useWsEvent: vi.fn(() => {}),
}));

vi.mock('@/shared/api/contracts/worldExplorer', () => ({
  acceptHypothesis: vi.fn(() =>
    Promise.resolve({ hypothesis_id: 'hyp_0001', status: 'accepted' }),
  ),
  rejectHypothesis: vi.fn(() =>
    Promise.resolve({ hypothesis_id: 'hyp_0001', status: 'rejected' }),
  ),
  getScenarios: vi.fn(() => Promise.resolve([])),
  supersedeScenario: vi.fn((scenarioId: string, supersededBy: string) =>
    Promise.resolve({
      scenario_id: scenarioId,
      status: 'superseded',
      superseded_by: supersededBy,
    }),
  ),
}));

import { useAuth } from '@/app/providers';
import { api } from '@/shared/lib/api';
import {
  acceptHypothesis,
  rejectHypothesis,
  getScenarios,
  supersedeScenario,
} from '@/shared/api/contracts/worldExplorer';
import WorldExplorerPage from '@/app/world-explorer/page';

afterEach(() => {
  cleanup();
  vi.mocked(api.get).mockReset();
  vi.mocked(acceptHypothesis).mockClear();
  vi.mocked(rejectHypothesis).mockClear();
  vi.mocked(getScenarios).mockClear();
  vi.mocked(supersedeScenario).mockClear();
});

const HYPOTHESIS = {
  id: 'hyp_0001',
  title: 'Тестовая гипотеза',
  description: 'Описание гипотезы',
  type: 'proactive',
  epoch: 'satya_yuga',
  confidence: 0.5,
  tags: [],
  status: 'proposed',
};

const SCENARIO_A = {
  id: 'sc_1',
  hypothesis_id: 'hyp_0001',
  title: 'Conservative',
  title_ru: 'Консервативный сценарий',
  description: 'Минимальные изменения',
  branch_type: 'conservative',
  quality_score: 0.6,
  tags: [],
  changes: 2,
  status: 'proposed',
  superseded_by: '',
  proposed_at: '2026-01-01T00:00:00+00:00',
  decided_at: '',
  decision_note: '',
};

const SCENARIO_B = {
  ...SCENARIO_A,
  id: 'sc_2',
  title: 'Radical',
  title_ru: 'Радикальный сценарий',
  branch_type: 'radical',
  quality_score: 0.8,
};

function mockApiForPage(hypotheses: unknown[] = []) {
  vi.mocked(api.get).mockImplementation((url: string) => {
    if (url.includes('/hypotheses/')) return Promise.resolve({ data: hypotheses });
    if (url.includes('epochs')) return Promise.resolve({ data: [] });
    if (url.includes('/stats')) return Promise.resolve({ data: {} });
    if (url.includes('feedback')) return Promise.resolve({ data: [] });
    if (url.includes('cache/stats')) return Promise.resolve({ data: {} });
    return Promise.reject(new Error('unmocked: ' + url));
  });
  vi.mocked(api.post).mockImplementation(() => Promise.reject(new Error('unmocked post')));
}

function renderAs(
  role: 'reader' | 'editor' | 'admin',
  hypotheses: unknown[] = [],
  scenarios: unknown[] = [],
) {
  mockApiForPage(hypotheses);
  vi.mocked(getScenarios).mockResolvedValue(scenarios as never);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  vi.mocked(useAuth).mockReturnValue({
    user: { id: '1', role, provider: 'test', is_active: true },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    establish: vi.fn(),
  } as never);
  return render(
    <QueryClientProvider client={client}>
      <WorldExplorerPage />
    </QueryClientProvider>
  );
}

describe('World Explorer dev-вкладки (Q4)', () => {
  it('reader: dev-вкладки «Поиск в источниках» и «Кэш» не отображаются', () => {
    renderAs('reader');
    expect(screen.queryByText('Кэш')).toBeNull();
    expect(screen.queryByText('Поиск в источниках')).toBeNull();
    // Обычные (не-dev) вкладки остаются
    expect(screen.getByText('Гипотезы')).toBeTruthy();
    expect(screen.getByText('Обратная связь')).toBeTruthy();
  });

  it('reader: автозагрузка /cache/stats не происходит', () => {
    renderAs('reader');
    const urls = vi.mocked(api.get).mock.calls.map((call) => String(call[0]));
    expect(urls.some((url) => url.includes('cache/stats'))).toBe(false);
  });

  it('editor: dev-вкладки отображаются', () => {
    renderAs('editor');
    expect(screen.getByText('Кэш')).toBeTruthy();
    expect(screen.getByText('Поиск в источниках')).toBeTruthy();
  });

  it('admin: dev-вкладки отображаются', () => {
    renderAs('admin');
    expect(screen.getByText('Кэш')).toBeTruthy();
    expect(screen.getByText('Поиск в источниках')).toBeTruthy();
  });
});

describe('World Explorer: решения по гипотезам (Этап 6a)', () => {
  it('editor видит «Принять»/«Отклонить» и подтверждение перед решением', async () => {
    renderAs('editor', [HYPOTHESIS]);
    fireEvent.click(screen.getByText('Гипотезы'));

    await waitFor(() => expect(screen.getByText('Тестовая гипотеза')).toBeTruthy());
    expect(screen.getByText('Принять')).toBeTruthy();
    expect(screen.getByText('Отклонить')).toBeTruthy();

    fireEvent.click(screen.getByText('Принять'));
    await waitFor(() => expect(screen.getByText('Принять гипотезу?')).toBeTruthy());
  });

  it('reader не видит кнопок решения', async () => {
    renderAs('reader', [HYPOTHESIS]);
    fireEvent.click(screen.getByText('Гипотезы'));

    await waitFor(() => expect(screen.getByText('Тестовая гипотеза')).toBeTruthy());
    expect(screen.queryByText('Принять')).toBeNull();
    expect(screen.queryByText('Отклонить')).toBeNull();
  });

  it('подтверждение вызывает acceptHypothesis', async () => {
    renderAs('editor', [HYPOTHESIS]);
    fireEvent.click(screen.getByText('Гипотезы'));
    await waitFor(() => expect(screen.getByText('Тестовая гипотеза')).toBeTruthy());

    fireEvent.click(screen.getByText('Принять'));
    await waitFor(() => expect(screen.getByText('Принять гипотезу?')).toBeTruthy());

    const buttons = screen.getAllByText('Принять');
    fireEvent.click(buttons[buttons.length - 1]);
    await waitFor(() => expect(acceptHypothesis).toHaveBeenCalledWith('hyp_0001'));
  });
});

describe('World Explorer: список сценариев и замена (Этап 6b)', () => {
  it('editor: список → выбор → замена → результат виден', async () => {
    renderAs('editor', [], [SCENARIO_A, SCENARIO_B]);
    fireEvent.click(screen.getByText('Сценарии'));

    await waitFor(() => expect(screen.getByText('Консервативный сценарий')).toBeTruthy());
    expect(screen.getByText('Радикальный сценарий')).toBeTruthy();
    expect(getScenarios).toHaveBeenCalledWith({ includeHistory: true, limit: 100 });

    fireEvent.click(screen.getByText('Консервативный сценарий'));
    fireEvent.click(screen.getByText('Заменить сценарий'));

    await waitFor(() => expect(screen.getByText('Заменить сценарий?')).toBeTruthy());
    const confirm = screen.getAllByText('Заменить');
    fireEvent.click(confirm[confirm.length - 1]);

    await waitFor(() =>
      expect(supersedeScenario).toHaveBeenCalledWith('sc_1', 'sc_2', ''),
    );
    await waitFor(() => expect(screen.getByText(/заменён на/)).toBeTruthy());
  });

  it('reader: видит список, но не видит действий замены', async () => {
    renderAs('reader', [], [SCENARIO_A, SCENARIO_B]);
    fireEvent.click(screen.getByText('Сценарии'));

    await waitFor(() => expect(screen.getByText('Консервативный сценарий')).toBeTruthy());
    expect(screen.queryByText('Заменить сценарий')).toBeNull();
    expect(screen.queryByText('Заменить')).toBeNull();
  });
});

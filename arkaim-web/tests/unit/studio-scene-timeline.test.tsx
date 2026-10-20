import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

beforeAll(() => {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserver as never;

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
});

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/studio',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/shared/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

import { api } from '@/shared/lib/api';
import { SceneTimelinePanel } from '@/app/studio/scene-timeline-panel';

const REPORT = {
  scenes: [
    {
      scene_id: 'scene_004',
      order_global: 4,
      title: '5. EXT. КОСМОС',
      epoch_id: 'pre_arkaim',
      epoch_name_ru: 'До Аркаима',
      temporal_node_id: 'temporal_pre_arkaim',
      event_ids: ['event_cosmic_impulse'],
      epoch_status: 'CONFIRMED',
      reason: '',
    },
    {
      scene_id: 'scene_000',
      order_global: 0,
      title: '1. EXT. ГЛУБОКИЙ КОСМОС',
      epoch_id: '',
      epoch_name_ru: '',
      temporal_node_id: '',
      event_ids: [],
      epoch_status: 'UNRESOLVED',
      reason: 'нет подтверждённой цепочки сцена → книжный чанк → claim → каноническое событие',
    },
  ],
  epochs: [
    {
      epoch_id: 'pre_arkaim',
      epoch_name_ru: 'До Аркаима',
      order: 0,
      temporal_node_id: 'temporal_pre_arkaim',
      scene_count: 1,
      scene_ids: ['scene_004'],
    },
  ],
  summary: {
    scene_count: 119,
    scenes_with_epoch: 11,
    scenes_without_epoch: 108,
    epoch_count: 4,
    coverage: 0.0924,
  },
  basis: 'подтверждённая цепочка',
  limitations: ['Эпоха проставляется только по подтверждённой цепочке до канонического события.'],
};

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SceneTimelinePanel />
    </QueryClientProvider>,
  );
}

describe('SceneTimelinePanel — временная линия сцен', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('показывает сводку покрытия и подтверждённые эпохи', async () => {
    vi.mocked(api.get).mockResolvedValue({ ok: true, data: REPORT });

    renderPanel();

    await waitFor(() => expect(screen.getByTestId('scene-timeline-panel')).toBeTruthy());

    expect(vi.mocked(api.get).mock.calls[0][0]).toBe('/api/studio/timeline');
    expect(screen.getByText('сцен: 119')).toBeTruthy();
    expect(screen.getByText('с подтверждённой эпохой: 11')).toBeTruthy();
    expect(screen.getByText('без эпохи: 108')).toBeTruthy();
    expect(screen.getByText(/покрытие: 9.2/)).toBeTruthy();
    expect(screen.getByText('До Аркаима')).toBeTruthy();
    expect(screen.getByText('scene_004')).toBeTruthy();
  });

  it('показывает честный блок сцен без подтверждённой эпохи', async () => {
    vi.mocked(api.get).mockResolvedValue({ ok: true, data: REPORT });

    renderPanel();

    await waitFor(() => expect(screen.getByTestId('scene-timeline-panel')).toBeTruthy());

    expect(screen.getByText(/Сцен без подтверждённой эпохи: 108/)).toBeTruthy();
    expect(screen.getByText('подтверждённая цепочка')).toBeTruthy();
  });

  it('не падает, если пришёл массив вместо отчёта', async () => {
    vi.mocked(api.get).mockResolvedValue({ ok: true, data: [] });

    renderPanel();

    await waitFor(() => expect(screen.getByText('Временная линия сцен недоступна.')).toBeTruthy());
  });
});

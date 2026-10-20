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

const pushMock = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  usePathname: () => '/studio',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/shared/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from '@/shared/lib/api';
import { WorldLinksPanel } from '@/app/studio/world-links-panel';
import type { Scene, WorldLinksReportT } from '@/app/studio/types';

const SCENE: Scene = { scene_id: 'scene_004', chapter: 0, title: '5. EXT. КОСМОС' };

const REPORT: WorldLinksReportT = {
  scene_id: 'scene_004',
  chapter: 0,
  links: [
    {
      link_type: 'event',
      status: 'CONFIRMED',
      target_kind: 'world_event',
      target_id: 'event_cosmic_impulse',
      target_label: 'Космический импульс и пробуждение носителя',
      basis: 'одобренная связь сценарию/книге → подтверждённая claim-связь → валидная цепочка',
      provenance: { category: 'AUTHOR_CANON', source_level: 'CANON', confidence: 1 },
      source_files: ['core/KNOWLEDGE/claim_temporal_links.json'],
    },
    {
      link_type: 'location',
      status: 'DERIVED',
      target_kind: 'world_location',
      target_id: 'атлантида',
      target_label: 'Атлантида',
      basis: "location_id сцены (LOCATION_VISUALS) дословно совпадает с name_ru локации World Model",
      provenance: { category: 'AUTHOR_CANON', source_level: 'CANON', confidence: 1 },
      source_files: ['core/CORE/narrative_engine/data/WORLD_MODEL.json'],
    },
    {
      link_type: 'location_mention',
      status: 'DERIVED',
      target_kind: 'world_location',
      target_id: 'аркаим',
      target_label: 'Аркаим',
      basis: 'одобренная метка crosswalk «Аркаим» дословно встречается в тексте сцены',
      provenance: { category: 'DERIVED', source_level: 'EXTERNAL_SOURCE', confidence: 0.8 },
      source_files: ['core/CORE/WORLD_CROSSWALK/WORLD_ENGINE_WORLD_MODEL.json'],
      mention_only: true,
    },
    {
      link_type: 'location',
      status: 'UNRESOLVED',
      target_kind: 'world_location',
      target_id: '',
      target_label: '',
      basis: "у локации сцены ('ПЕЩЕРА') нет точного соответствия в World Model",
      provenance: {},
      source_files: ['core/CORE/narrative_engine/data/WORLD_MODEL.json'],
    },
  ],
  summary: { total: 4, confirmed: 1, derived: 2, unresolved: 1, ambiguous: 0 },
  missing: {
    location: 'у локации сцены нет точного соответствия в World Model',
    event: 'нет подтверждённой цепочки сцена → книжный чанк → claim → каноническое событие',
  },
  provenance: { world_links: 'MIXED' },
};

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WorldLinksPanel scene={SCENE} />
    </QueryClientProvider>,
  );
}

describe('WorldLinksPanel', () => {
  beforeEach(() => {
    pushMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('группирует связи по статусу и показывает происхождение', async () => {
    vi.mocked(api.get).mockResolvedValue({ ok: true, data: REPORT });

    renderPanel();

    await waitFor(() => expect(screen.getByTestId('world-links-panel')).toBeTruthy());

    expect(screen.getByText(/^Подтверждённые связи · 1/)).toBeTruthy();
    expect(screen.getByText(/^Производные связи · 1/)).toBeTruthy();
    expect(screen.getByText(/^Упоминания локаций · 1/)).toBeTruthy();
    expect(screen.getByText(/^Нет данных · 1/)).toBeTruthy();

    // Подтверждённое событие показывается со своим статусом.
    expect(screen.getByText('Космический импульс и пробуждение носителя')).toBeTruthy();
    expect(screen.getByText('подтверждено')).toBeTruthy();
    expect(screen.getAllByText(/Происхождение: AUTHOR_CANON · уровень CANON · уверенность 1/).length).toBeGreaterThan(0);

    // Производная связь не выдаётся за подтверждённую.
    expect(screen.getAllByText('производное').length).toBeGreaterThan(0);

    // Нерешённая связь показана как отсутствие данных с причиной.
    expect(screen.getAllByText(/Причина: у локации сцены нет точного соответствия/).length).toBeGreaterThan(0);
  });

  it('не смешивает упоминание локации с локацией сцены', async () => {
    vi.mocked(api.get).mockResolvedValue({ ok: true, data: REPORT });

    renderPanel();

    await waitFor(() => expect(screen.getByTestId('world-links-panel')).toBeTruthy());

    const mentions = screen.getByTestId('world-link-group-Упоминания локаций');
    expect(mentions.textContent).toContain('упоминание в тексте, не место действия');
    expect(mentions.textContent).toContain('Аркаим');

    const derived = screen.getByTestId('world-link-group-Производные связи');
    expect(derived.textContent).toContain('Атлантида');
    expect(derived.textContent).not.toContain('Аркаим');
  });

  it('запрашивает точечный read-only эндпоинт сцены', async () => {
    vi.mocked(api.get).mockResolvedValue({ ok: true, data: REPORT });

    renderPanel();

    await waitFor(() => expect(screen.getByTestId('world-links-panel')).toBeTruthy());

    expect(vi.mocked(api.get).mock.calls[0][0]).toBe('/api/studio/scenes/scene_004/world-links?chapter=0');
  });

  it('пустое состояние показывает причины отсутствия данных', async () => {
    vi.mocked(api.get).mockResolvedValue({
      ok: true,
      data: {
        scene_id: 'scene_013',
        chapter: 0,
        links: [],
        summary: { total: 0, confirmed: 0, derived: 0, unresolved: 0, ambiguous: 0 },
        missing: { location: 'у локации сцены нет точного соответствия в World Model' },
        provenance: { world_links: 'ABSENT' },
      },
    });

    renderPanel();

    await waitFor(() =>
      expect(screen.getByText('Для этой сцены подтверждённых связей с миром не найдено.')).toBeTruthy(),
    );
    expect(screen.getByText(/у локации сцены нет точного соответствия в World Model/)).toBeTruthy();
  });

  it('не падает, если пришёл массив вместо отчёта', async () => {
    vi.mocked(api.get).mockResolvedValue({ ok: true, data: [] });

    renderPanel();

    await waitFor(() => expect(screen.getByText('Связи сцены с миром недоступны.')).toBeTruthy());
  });
});

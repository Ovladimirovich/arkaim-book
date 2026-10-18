import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
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
import { ContinuityPanel } from '@/app/studio/continuity-panel';
import { FilmTree } from '@/app/studio/film-tree';
import type {
  MatchContextT,
  SceneContinuityReportT,
  StudioSessionT,
  FilmT,
} from '@/app/studio/types';

const SESSION = {
  session_id: 'sess_1',
  user_id: '1',
  title: 'тест',
  chapter: 1,
  scene_id: 'scene_1',
  context_type: 'scene',
  active_version_id: 'ver_1',
  status: 'draft',
  approved_image_asset_id: null,
  reference_assets: [],
  created_at: '2026-10-15T00:00:00',
  updated_at: '2026-10-15T00:00:00',
  finalized_at: null,
} as StudioSessionT;

const REPORT: SceneContinuityReportT = {
  scene: {
    scene_id: 'scene_1',
    chapter: 1,
    order_global: 1,
    title: 'Сцена 1',
    location: 'Аркаим',
    location_reference_asset_id: null,
    time_of_day: 'dawn',
    season: '',
    weather: '',
    lighting_direction: 'east, low',
    lighting_color: '',
    palette: ['gold'],
    visual_style: 'cinematic_fantasy',
    emotion: 'joy',
    characters: [],
    approved_image_asset_id: null,
    has_session: true,
    session_id: 'sess_1',
    has_scenario: true,
    shot_count: 2,
    shots: [],
    art_direction_revision: 2,
    known_fields: ['location', 'lighting'],
    provenance: { location: 'genome' },
  },
  links: [
    {
      link_id: 'adjacent_scenes:scene_0->scene_1',
      link_key: 'adjacent_scenes:scene_0->scene_1',
      relation: 'adjacent_scenes',
      certainty: 'confirmed',
      from_ref: 'scene_0',
      to_ref: 'scene_1',
      from_scene_id: 'scene_0',
      to_scene_id: 'scene_1',
      status: 'mismatch',
      findings: [
        {
          field: 'lighting',
          kind: 'difference',
          severity: 'warning',
          message: 'Одинаковая локация и время, но разное направление света',
          subject: '',
          from_value: 'west',
          to_value: 'east, low',
          certainty: 'confirmed',
          sources: ['visual_context'],
        },
      ],
      reason: '',
      decision: null,
      clip_boundary: {
        previous_clip_asset_id: null,
        end_frame_asset_id: 'asset_0',
        next_clip_asset_id: null,
        start_frame_asset_id: 'asset_1',
        status: 'declared',
        note: '',
      },
      basis: { scene_id: 'scene_1', art_direction_revision: 2, from_approved: 'asset_0', to_approved: 'asset_1' },
    },
    {
      link_id: 'cross_episode:scene_5->scene_1',
      link_key: 'cross_episode:scene_5->scene_1',
      relation: 'cross_episode',
      certainty: 'candidate',
      from_ref: 'scene_5',
      to_ref: 'scene_1',
      from_scene_id: 'scene_5',
      to_scene_id: 'scene_1',
      status: 'consistent',
      findings: [
        {
          field: 'location',
          kind: 'change',
          severity: 'info',
          message: 'Смена локации между сценами — проверьте, что это намеренно',
          subject: '',
          from_value: 'Аудитория',
          to_value: 'Аркаим',
          certainty: 'candidate',
          sources: ['genome'],
        },
      ],
      reason: 'Общая сюжетная метка генома: передача',
      decision: null,
      clip_boundary: null,
      basis: {},
    },
  ],
  overall_status: 'mismatch',
  limitations: ['Визуальный контекст не запрашивался (with_context=false) — окружение/свет/палитра не сравнивались.'],
  neighbors: { prev_scene_id: 'scene_0', next_scene_id: 'scene_2' },
  episode: { chapter: 1, index_in_episode: 1, scene_count: 6 },
};

const MATCH_CONTEXT: MatchContextT = {
  available: true,
  from_scene_id: 'scene_0',
  to_scene_id: 'scene_1',
  constraints: { location: 'Аркаим', lighting: 'east, low' },
  sources: { location: 'genome', lighting: 'visual_context' },
  remaining_differences: [
    {
      field: 'lighting',
      kind: 'difference',
      severity: 'warning',
      message: 'Разница в свете сохранится',
      subject: '',
      from_value: 'west',
      to_value: 'east',
      certainty: 'confirmed',
      sources: ['visual_context'],
    },
  ],
  prompt_changes: [
    { shot_id: 'shot_1', changed: true, before: 'БЫЛО_1', after: 'СТАЛО_1' },
    { shot_id: 'shot_2', changed: false, before: 'БЫЛО_2', after: 'БЫЛО_2' },
  ],
  applied: false,
  note: 'Предпросмотр. Исходный сценарий и промпты НЕ изменены — перенос применяется отдельным решением режиссёра.',
  limitations: [],
};

function installApiMocks() {
  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.includes('/continuity/match-context')) {
      return Promise.resolve({ ok: true, data: MATCH_CONTEXT });
    }
    if (path.includes('/continuity')) {
      return Promise.resolve({ ok: true, data: REPORT });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);

  vi.mocked(api.post).mockImplementation((() =>
    Promise.resolve({ ok: true, data: {} })) as never);
  vi.mocked(api.delete).mockImplementation((() =>
    Promise.resolve({ ok: true, data: {} })) as never);
}

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ContinuityPanel session={SESSION} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  installApiMocks();
});

describe('Панель связности сцены (Continuity)', () => {
  it('показывает состояние сцены, связи, причины и контракт клипов', async () => {
    renderPanel();

    const panel = await screen.findByTestId('continuity-panel');
    expect(panel.textContent).toContain('есть потенциальное несоответствие');

    const links = screen.getAllByTestId('continuity-link');
    expect(links.length).toBe(2);
    expect(panel.textContent).toContain('Соседние сцены эпизода');
    expect(panel.textContent).toContain('Смысловая связь разных эпизодов');
    expect(panel.textContent).toContain('разное направление света');
    expect(panel.textContent).toContain('Общая сюжетная метка генома: передача');
    // Контракт клипов: объявленные кадры
    expect(panel.textContent).toContain('asset_0');
    expect(panel.textContent).toContain('asset_1');
    // Кандидат по слабой связи не выдаётся за несоответствие
    expect(panel.textContent).toContain('предположение');
  });

  it('кнопка «Разрешить отличие» сохраняет решение с link_key и basis', async () => {
    renderPanel();

    const waive = await screen.findByText('Разрешить отличие');
    fireEvent.click(waive);

    await waitFor(() =>
      expect(vi.mocked(api.post)).toHaveBeenCalledWith('/api/studio/continuity/decisions', {
        link_key: 'adjacent_scenes:scene_0->scene_1',
        basis: { scene_id: 'scene_1', art_direction_revision: 2, from_approved: 'asset_0', to_approved: 'asset_1' },
        session_id: 'sess_1',
        note: '',
      }),
    );
  });

  it('«Согласовать со сценой» показывает предпросмотр без применения', async () => {
    renderPanel();

    fireEvent.click(await screen.findByText('Согласовать со сценой'));

    const preview = await screen.findByTestId('match-context');
    expect(preview.textContent).toContain('Аркаим');
    expect(preview.textContent).toContain('БЫЛО_1');
    expect(preview.textContent).toContain('СТАЛО_1');
    expect(preview.textContent).toContain('без изменений'); // shot_2 не изменится
    expect(preview.textContent).toContain('НЕ изменены');
    // Ничего не применялось автоматически
    expect(vi.mocked(api.post)).not.toHaveBeenCalledWith(
      expect.stringContaining('/continuity/apply'),
      expect.anything(),
    );
  });
});

function installAppliedMock(applied: boolean, stale = false) {
  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.includes('/continuity/match-context')) {
      return Promise.resolve({ ok: true, data: { ...MATCH_CONTEXT, applied, applied_stale: stale } });
    }
    if (path.includes('/continuity')) {
      return Promise.resolve({ ok: true, data: REPORT });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);
}

describe('Применение переноса ограничений (Фаза 2)', () => {
  it('кнопка «Применить к сцене» вызывает POST /continuity/apply', async () => {
    renderPanel();

    const btn = await screen.findByText('Применить к сцене');
    fireEvent.click(btn);

    await waitFor(() =>
      expect(vi.mocked(api.post)).toHaveBeenCalledWith('/api/studio/sess_1/continuity/apply', { note: '' }),
    );
  });

  it('применённый перенос показывает метку и позволяет отменить', async () => {
    installAppliedMock(true);
    renderPanel();

    const panel = await screen.findByTestId('continuity-panel');
    await waitFor(() => expect(panel.textContent).toContain('перенос применён'));

    fireEvent.click(await screen.findByText('Отменить применение'));

    await waitFor(() =>
      expect(vi.mocked(api.delete)).toHaveBeenCalledWith('/api/studio/sess_1/continuity/apply'),
    );
  });

  it('устаревший перенос помечается и не выдаётся за действующий', async () => {
    installAppliedMock(false, true);
    renderPanel();

    const panel = await screen.findByTestId('continuity-panel');
    await waitFor(() => expect(panel.textContent).toContain('перенос устарел'));
    expect(screen.queryByText('Отменить применение')).toBeNull();
    expect(screen.getByText('Применить к сцене')).toBeTruthy();
  });
});

const FILM: FilmT = {
  film: {
    book_id: 'nasledie-arkaima',
    title: 'Наследие Аркаима',
    episode_count: 1,
    scene_count: 1,
    total_duration_sec: 12,
  },
  episodes: [
    {
      episode_id: 'chapter_1',
      chapter: 1,
      title: 'Глава 1',
      scene_count: 1,
      total_duration_sec: 12,
      scenes: [
        {
          scene_id: 'scene_1',
          chapter: 1,
          index_in_episode: 0,
          order_global: 0,
          title: 'Сцена 1',
          location: 'Аркаим',
          characters: [],
          emotion: '',
          visual_style_hint: '',
          has_session: true,
          session_id: 'sess_1',
          session_status: 'draft',
          approved_image_asset_id: null,
          shot_count: 2,
          total_duration_sec: 12,
          video_count: 0,
          has_video: false,
          status: 'prompts',
          shots: [],
        },
      ],
    },
  ],
};

describe('Дерево фильма — метка связности', () => {
  it('показывает предупреждение связности на сцене с несоответствием', () => {
    render(
      <FilmTree
        film={FILM}
        selectedKey={null}
        onSelect={vi.fn()}
        continuity={{
          scene_1: {
            overall_status: 'mismatch',
            mismatch_count: 2,
            waived_count: 0,
            pending_count: 0,
            link_count: 3,
          },
        }}
      />,
    );

    expect(screen.getByText('связность: 2')).toBeTruthy();
  });

  it('без данных связности метки нет', () => {
    render(<FilmTree film={FILM} selectedKey={null} onSelect={vi.fn()} />);
    expect(screen.queryByText(/связность:/)).toBeNull();
  });
});

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

  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
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
import { AffectedPanel } from '@/app/studio/affected-panel';
import type {
  ArtDirectionApplyT,
  ArtDirectionT,
  PreparedUpdateT,
  StudioSessionT,
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

const AD: ArtDirectionT = {
  ad_id: 'film',
  revision: 2,
  style_preset: 'cinematic_fantasy',
  style_prompt: 'общий стиль фильма',
  palette: ['иней'],
  characters: [],
  locations: [],
  reference_asset_ids: [],
  last_change_sections: ['palette'],
};

const APPLIED = {
  style_preset: 'cinematic_fantasy',
  style_prompt: 'общий стиль фильма',
  palette: ['иней'],
  aspect_ratio: '16:9',
  composition_rules: [],
  lighting_rules: [],
  negative_rules: [],
  preset_negative_additions: [],
  characters: [],
  location: null,
  reference_asset_ids: [],
  revision: 2,
};

const AFFECTED = [
  {
    asset_id: 'asset_old_1',
    asset_type: 'image',
    title: 'старый кадр сцены',
    status: 'completed',
    reasons: ['общие правила обновлялись после генерации (rev 1 → 2)'],
    created_at: '2026-10-15T00:00:00',
    prompt_used: 'СТАРЫЙ_ПРОМПТ',
    shot_id: null,
    shot: null,
    frame_status: 'needs_update',
    prepared: null,
  },
  {
    asset_id: 'asset_video_1',
    asset_type: 'video',
    title: 'видео сцены',
    status: 'completed',
    reasons: ['кадр-основа не совпадает с утверждённым кадром сцены'],
    created_at: '2026-10-15T00:00:00',
    prompt_used: 'ВИДЕО',
    shot_id: null,
    shot: null,
    frame_status: 'needs_update',
    prepared: null,
  },
];

const PREPARED: PreparedUpdateT = {
  prepared_id: 'prep_1',
  session_id: 'sess_1',
  shot_id: 'shot_001',
  source_asset_id: 'asset_old_1',
  new_prompt: 'ИТОГ_ШОТА_0, color palette: иней',
  negative_prompt: ['cartoon'],
  motion_prompt: '',
  applied_rules: APPLIED,
  reference_asset_ids: ['ast_ref'],
  backend: 'mock',
  workflow: 'mock',
  expected_result_type: 'image',
  status: 'prepared',
  new_asset_id: null,
  created_at: '2026-10-15T01:00:00',
  updated_at: '2026-10-15T01:00:00',
};

const EXECUTORS = {
  mock: {
    label: 'mock — тестовый ответ',
    execution: 'local',
    execution_label: 'локальный (тестовые ответы)',
    available: true,
    why: 'без трат, проверка цикла подготовки и сравнения',
    requirements: 'нет',
    workflow: 'mock',
  },
  agnes: {
    label: 'agnes — ComfyUI-Agnes (бесплатный)',
    execution: 'cloud',
    execution_label: 'облачный (arkaim-media → Agnes)',
    available: true,
    why: 'реальная генерация без платных кредитов',
    requirements: 'доступность Agnes',
    workflow: 'agnes-image',
  },
};

const APPLY: ArtDirectionApplyT = {
  art_direction: AD,
  scene: {
    scene_id: 'scene_1',
    chapter: 1,
    title: 'СЦЕНА',
    location: '',
    characters: [],
    approved_image_asset_id: null,
  },
  episode: {
    shot_count: 2,
    total_duration_sec: 7,
    style_label: 'cinematic_fantasy',
    revision: 2,
    last_change_sections: ['palette'],
  },
  shots: [
    {
      shot_index: 0,
      shot_id: 'shot_001',
      order: 0,
      shot_type: 'establishing',
      duration_sec: 3,
      approved_image_asset_id: null,
      applied: APPLIED,
      local_overrides: {},
      resolved_prompt: 'ИТОГ_ШОТА_0, color palette: иней',
      resolved_negative: ['cartoon'],
    },
    {
      shot_index: 1,
      shot_id: 'shot_002',
      order: 1,
      shot_type: 'medium',
      duration_sec: 4,
      approved_image_asset_id: null,
      applied: APPLIED,
      local_overrides: {},
      resolved_prompt: 'ИТОГ_ШОТА_1',
      resolved_negative: [],
    },
  ],
  affected_artifacts: AFFECTED,
  prepared_updates: [],
  stale_videos: [
    {
      asset_id: 'asset_video_1',
      title: 'видео сцены',
      reference_image_id: 'asset_prev',
      current_approved: 'asset_new',
      reason: 'видео основано на предыдущем кадре (требует обновления)',
    },
  ],
};

type ApiState = {
  apply: ArtDirectionApplyT;
  prepared: PreparedUpdateT[];
};

let state: ApiState;

function installApiMocks() {
  state = { apply: APPLY, prepared: [] };

  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.includes('/art-direction/apply')) {
      return Promise.resolve({ ok: true, data: state.apply });
    }
    if (path.includes('/prepared-updates')) {
      return Promise.resolve({ ok: true, data: { prepared_updates: state.prepared, executors: EXECUTORS } });
    }
    if (path.includes('/book/assets/')) {
      return Promise.resolve({ ok: true, data: { asset_id: 'a', status: 'generating' } });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);

  vi.mocked(api.post).mockImplementation(((path: string, body?: unknown) => {
    if (path.includes('/prepared-updates')) {
      const req = (body || {}) as { shot_id?: string; source_asset_id?: string; backend?: string };
      const created: PreparedUpdateT = {
        ...PREPARED,
        prepared_id: 'prep_new',
        shot_id: req.shot_id || PREPARED.shot_id,
        source_asset_id: req.source_asset_id ?? null,
        backend: req.backend || 'mock',
        status: 'prepared',
      };
      state.prepared = [...state.prepared, created];
      return Promise.resolve({ ok: true, data: { prepared: created } });
    }
    if (path.includes('/image-jobs')) {
      return Promise.resolve({ ok: true, data: { asset_id: 'asset_new_variant', status: 'generating' } });
    }
    return Promise.resolve({ ok: true, data: {} });
  }) as never);

  vi.mocked(api.patch).mockImplementation((() =>
    Promise.resolve({ ok: true, data: { ...PREPARED, status: 'generating' } })) as never);
}

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AffectedPanel session={SESSION} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  installApiMocks();
});

describe('Панель затронутых кадров', () => {
  it('показывает затронутый кадр: причина, промпты, статус, план, кнопка подготовки', async () => {
    renderPanel();

    const panel = await screen.findByTestId('affected-panel');
    expect(panel.textContent).toContain('требуют обновления: 2');

    const card = await screen.findByTestId('affected-card-asset_old_1');
    // title/статус — в заголовке LCard (вне data-testid div); текст встречается и в чекбоксе массового выбора
    expect(screen.getAllByText('старый кадр сцены').length).toBeGreaterThan(0);
    expect(screen.getAllByText('требует обновления').length).toBeGreaterThan(0);
    expect(card.textContent).toContain('общие правила обновлялись после генерации');
    expect(card.textContent).toContain('СТАРЫЙ_ПРОМПТ');
    expect(card.textContent).toContain('ИТОГ_ШОТА_0');

    // Кнопка подготовки (изображение; видео без подготовки)
    expect(screen.getByTestId('prepare-asset_old_1')).toBeTruthy();
    expect(screen.queryByTestId('prepare-asset_video_1')).toBeNull();

    // Видео на предыдущем кадре: связь сохраняется, автогенерации нет
    const stale = await screen.findByTestId('stale-videos');
    expect(stale.textContent).toContain('требует обновления');
    expect(stale.textContent).toContain('старое видео не удаляется');
  }, 60000);

  it('«Подготовить обновление» уходит POST-ом без генерации (shot + source)', async () => {
    renderPanel();

    const btn = await screen.findByTestId('prepare-asset_old_1');
    fireEvent.click(btn.querySelector('button')!);

    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        '/api/studio/sess_1/prepared-updates',
        expect.objectContaining({
          shot_id: 'shot_001',
          source_asset_id: 'asset_old_1',
          backend: 'mock',
        }),
      );
    });

    // Задание появляется в карточках подготовленных заданий
    expect(await screen.findByTestId('prepared-title-prep_new')).toBeTruthy();
  }, 60000);

  it('массовый выбор: чекбокс → подготовить несколько → сводка изменений', async () => {
    renderPanel();

    const check = await screen.findByTestId('affected-check-asset_old_1');
    fireEvent.click(check);

    const massBtn = screen.getByRole('button', { name: /Подготовить обновление \(1\)/ });
    fireEvent.click(massBtn);

    await waitFor(() => {
      expect(screen.getByTestId('mass-summary')).toBeTruthy();
    });
    const summary = screen.getByTestId('mass-summary');
    expect(summary.textContent).toContain('старый кадр сцены');
    expect(summary.textContent).toContain('shot_001');
    expect(summary.textContent).toContain('Генерация не запускалась');
  }, 60000);
});

describe('Подготовленное задание: исполнитель и mock-генерация', () => {
  it('карточка задания: справочник исполнителей и запуск через image-jobs', async () => {
    state.prepared = [PREPARED];

    renderPanel();

    const card = await screen.findByTestId('prepared-title-prep_1');
    expect(card).toBeTruthy();
    const panel = screen.getByTestId('affected-panel');

    // Справочник исполнителя (почему выбран, требования, локальный/облачный)
    expect(panel.textContent).toContain('без трат, проверка цикла подготовки');
    expect(panel.textContent).toContain('локальный (тестовые ответы)');

    // Запуск генерации — штатный image-jobs + PATCH статуса задания
    const gen = await screen.findByTestId('generate-prep_1');
    fireEvent.click(gen.querySelector('button')!);

    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        '/api/studio/image-jobs',
        expect.objectContaining({
          prompt: 'ИТОГ_ШОТА_0, color palette: иней',
          preferred_backend: 'mock',
          shot_id: 'shot_001',
          plan_id: 'prep:prep_1',
        }),
      );
    });
    await waitFor(() => {
      expect(vi.mocked(api.patch)).toHaveBeenCalledWith(
        '/api/studio/sess_1/prepared-updates/prep_1',
        expect.objectContaining({ status: 'generating', new_asset_id: 'asset_new_variant' }),
      );
    });
  }, 60000);
});

describe('Сравнение и утверждение нового кадра', () => {
  it('done-задание: сравнение старый↔новый и «Утвердить новый кадр»', async () => {
    state.prepared = [{ ...PREPARED, status: 'done', new_asset_id: 'asset_new_variant' }];

    renderPanel();

    const compare = await screen.findByTestId('compare-prep_1');
    fireEvent.click(compare.querySelector('button')!);

    const modal = await screen.findByTestId('compare-modal');
    expect(modal.textContent).toContain('Старый кадр');
    expect(modal.textContent).toContain('Новый кадр');
    expect(modal.textContent).toContain('СТАРЫЙ_ПРОМПТ');
    expect(modal.textContent).toContain('ИТОГ_ШОТА_0');
    expect(modal.textContent).toContain('какие правила изменились');
    expect(modal.textContent).toContain('ревизия правил на момент подготовки');
    expect(modal.textContent).toContain('утверждённый кадр сцены сейчас');
    expect(modal.textContent).toContain('не удаляет старый кадр');

    fireEvent.click(screen.getByTestId('approve-new-frame').querySelector('button')!);

    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        '/api/studio/sess_1/prepared-updates/prep_1/approve',
      );
    });
  }, 60000);
});

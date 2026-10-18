import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Polyfill browser APIs for antd
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
  usePathname: () => '/studio',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(() => ({ isDark: false, toggle: vi.fn() })),
}));

vi.mock('@/shared/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

import { useAuth } from '@/app/providers';
import { api } from '@/shared/lib/api';

const SCENES = [{ scene_id: 'scene_1', chapter: 1, title: 'Гиперборея' }];

/** Дерево фильма из плоского списка сцен (как отдаёт GET /studio/film). */
function filmFromScenes(scenes: typeof SCENES) {
  const byChapter = new Map<number, typeof SCENES>();
  scenes.forEach((s) => {
    if (!byChapter.has(s.chapter)) byChapter.set(s.chapter, []);
    byChapter.get(s.chapter)!.push(s);
  });
  const episodes = Array.from(byChapter.entries()).map(([chapter, list]) => ({
    episode_id: `chapter_${chapter}`,
    chapter,
    title: `Глава ${chapter}`,
    scene_count: list.length,
    total_duration_sec: 0,
    scenes: list.map((s, i) => ({
      scene_id: s.scene_id,
      chapter: s.chapter,
      index_in_episode: i,
      order_global: i,
      title: s.title,
      location: '',
      characters: [],
      emotion: '',
      visual_style_hint: '',
      has_session: false,
      session_id: null,
      session_status: null,
      approved_image_asset_id: null,
      shot_count: 0,
      total_duration_sec: 0,
      video_count: 0,
      has_video: false,
      status: 'no_session' as const,
      shots: [],
    })),
  }));
  return {
    film: {
      book_id: 'nasledie-arkaima',
      title: '',
      episode_count: episodes.length,
      scene_count: scenes.length,
      total_duration_sec: 0,
    },
    episodes,
  };
}

const SHOTS = [
  {
    shot_id: 'shot_001',
    order: 0,
    shot_type: 'establishing',
    description: 'ОПИСАНИЕ_0',
    duration_sec: 3,
    camera_action: 'static',
    camera_angle: 'eye_level',
    provenance: { source: 'genome', source_id: 'scene_1', confidence: 0.9 },
    character_actions: [{ character_name: 'Велик', action: 'стоит у края' }],
    environment_actions: [],
  },
  {
    shot_id: 'shot_002',
    order: 1,
    shot_type: 'medium',
    description: 'ОПИСАНИЕ_1',
    duration_sec: 4,
    camera_action: 'slow dolly in',
    provenance: { source: 'video_intelligence', confidence: 0.8 },
    character_actions: [],
    environment_actions: [{ element: 'fog', action: 'rising' }],
  },
];

const VERSION = {
  version_id: 'ver_1',
  session_id: 'sess_1',
  version_number: 3,
  image_description: {
    plan_id: 'plan_img_1',
    prompt: 'КАДР_ПРОМПТ_1',
    negative_constraints: [],
    media_kind: 'image',
  },
  video_description: {
    plan_id: 'plan_vid_1',
    prompt: 'ВИДЕО_ПРОМПТ_1',
    duration_sec: 8,
    fps: 24,
    motion: { camera_motion: 'slow_push_in' },
  },
  video_scenario: {
    scenario_id: 'sc_1',
    synopsis: 'СИНОПСИС_1',
    direction_notes: 'РЕЖИССЁРСКОЕ_УКАЗАНИЕ',
    shots: SHOTS,
    provenance: [{ source: 'genome', confidence: 0.9 }],
  },
  parent_version_id: 'ver_0',
  derivation: 'adaptation',
  user_modifications: [],
  is_active: true,
  is_final: false,
  created_by: 'user',
  created_at: '2026-10-15T00:00:00',
  note: 'edit',
};

const makeSession = () => ({
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
});

/** Кадр по текущему промпту. */
const IMAGE_CURRENT = {
  asset_id: 'asset_img_current',
  asset_type: 'image',
  chapter: 1,
  scene_id: 'scene_1',
  title: 'кадр: Гиперборея',
  status: 'completed',
  file_path: 'images/asset_img_current.png',
  error: null,
  prompt_used: 'КАДР_ПРОМПТ_1',
  generation: { provider: 'agnes', plan_id: 'plan_img_1' },
};

/** Кадр по прежнему промпту (промпт менялся после генерации). */
const IMAGE_OUTDATED = {
  asset_id: 'asset_img_old',
  asset_type: 'image',
  chapter: 1,
  scene_id: 'scene_1',
  title: 'старый кадр',
  status: 'completed',
  file_path: 'images/asset_img_old.png',
  error: null,
  prompt_used: 'ПРОЖНИЙ_ПРОМПТ_ДО_ПРАВКИ',
  generation: { provider: 'agnes', plan_id: 'plan_img_1' },
};

/** mock-видео, сделанное по другому промпту → потенциально устарело. */
const VIDEO_STALE_MOCK = {
  asset_id: 'asset_vid_stale',
  asset_type: 'video',
  chapter: 1,
  scene_id: 'scene_1',
  title: 'mock-клип',
  status: 'completed',
  file_path: 'videos/asset_vid_stale.mp4',
  error: null,
  duration_sec: 8,
  fps: 24,
  prompt_used: 'ИНОЙ_ПРОМПТ_ДВИЖЕНИЯ',
  generation: { provider: 'mock', backend: 'mock', plan_id: 'plan_vid_1' },
};

/** Реальный клип без признаков устаревания. */
const VIDEO_REAL = {
  asset_id: 'asset_vid_real',
  asset_type: 'video',
  chapter: 1,
  scene_id: 'scene_1',
  title: 'реальный клип',
  status: 'completed',
  file_path: 'videos/asset_vid_real.mp4',
  error: null,
  duration_sec: 8,
  fps: 24,
  prompt_used: 'ВИДЕО_ПРОМПТ_1. движение камеры: slow_push_in',
  generation: { provider: 'comfyicu', backend: 'comfyicu', plan_id: 'plan_vid_1' },
};

function mockAuth(role = 'editor') {
  vi.mocked(useAuth).mockReturnValue({
    user: {
      id: '1',
      role,
      provider: 'dev',
      is_active: true,
      username: 'test',
      display_name: 'Test User',
    },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    establish: vi.fn(),
  } as never);
}

// ── Единый визуальный язык фильма (art direction) — фикстуры ────

const AD = {
  ad_id: 'film',
  revision: 2,
  updated_at: '2026-10-15T00:00:00',
  style_preset: 'cinematic_fantasy',
  style_prompt: 'общий стиль фильма',
  palette: ['иней', 'лазурь'],
  aspect_ratio: null,
  composition_rules: ['место для титров снизу'],
  lighting_rules: ['мягкий боковой свет'],
  negative_rules: [],
  characters: [{ knowledge_key: 'Велик', name: 'Велик', approved_image_asset_id: null, note: '' }],
  locations: [],
  reference_asset_ids: [],
  last_change_sections: ['style', 'palette'],
};

const AD_LIBRARY = {
  styles: {
    cinematic_fantasy: {
      prefix: 'cinematic fantasy film still',
      aspect_ratio: '16:9',
      description: 'кинематографическое фэнтези',
      negative_additions: ['cartoon'],
    },
    realistic: { prefix: 'realistic photo', aspect_ratio: '16:9', description: '', negative_additions: [] },
  },
  characters: { Велик: { name: 'Велик', build: 'высокий' } },
  locations: { Гиперборея: { name: 'Гиперборея', type: 'city', palette: ['иней', 'камень'] } },
};

const AD_APPLY = {
  art_direction: AD,
  scene: {
    scene_id: 'scene_1',
    chapter: 1,
    title: 'Гиперборея',
    location: '',
    characters: [],
    approved_image_asset_id: null,
  },
  episode: {
    shot_count: SHOTS.length,
    total_duration_sec: 7,
    style_label: 'cinematic_fantasy',
    revision: 2,
    last_change_sections: ['style', 'palette'],
  },
  shots: SHOTS.map((s, i) => ({
    shot_index: i,
    shot_id: s.shot_id,
    order: s.order,
    shot_type: s.shot_type,
    duration_sec: s.duration_sec,
    applied: {
      style_preset: AD.style_preset,
      style_prompt: AD.style_prompt,
      palette: AD.palette,
      aspect_ratio: '16:9',
      composition_rules: AD.composition_rules,
      lighting_rules: AD.lighting_rules,
      negative_rules: AD.negative_rules,
      preset_negative_additions: ['cartoon'],
      characters: [],
      location: null,
      reference_asset_ids: [],
      revision: AD.revision,
    },
    local_overrides: i === 0 ? { style_override: 'локальный стиль плана' } : {},
    resolved_prompt: `общий стиль фильма, color palette: иней, лазурь, ${s.description}, ИТОГ_${i}`,
    resolved_negative: ['cartoon'],
  })),
  affected_artifacts: [
    {
      asset_id: 'asset_img_old',
      asset_type: 'image',
      title: 'старый кадр',
      status: 'completed',
      reasons: ['общие правила обновлялись после генерации (rev 1 → 2)'],
      created_at: '2026-10-15T00:00:00',
    },
  ],
};

/** Валидный (пустой) план сборки последовательности: как его отдаёт GET /studio/sequence.
 *  Секция FilmSequence читает plan.summary — мокаем полный контракт, а не массив []. */
const SEQUENCE_PLAN = {
  segments: [],
  assembled: [],
  gaps: [],
  transitions: [],
  executors: [],
  executor_mixed: false,
  summary: {
    segment_count: 0,
    scene_count: 1,
    episode_count: 1,
    clip_count: 0,
    ready_count: 0,
    frame_count: 0,
    placeholder_count: 0,
    mock_count: 0,
    stale_count: 0,
    assembled_count: 0,
    gap_count: 0,
    executor_count: 0,
    total_duration_sec: 0,
    assembled_duration_sec: 0,
    gap_duration_sec: 0,
  },
  limitations: [],
  plan_text: 'План сборки последовательности фильма',
  edl_xml: null,
  scope: 'film',
  chapter: null,
  scene_ids: ['scene_1'],
  film: { book_id: 'nasledie-arkaima', title: '', episode_count: 1 },
};

let created = false;

function installApiMocks() {
  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.startsWith('/api/studio/film')) {
      return Promise.resolve({ ok: true, data: filmFromScenes(SCENES) });
    }
    if (path.startsWith('/api/studio/sequence')) {
      return Promise.resolve({ ok: true, data: SEQUENCE_PLAN });
    }
    if (path.startsWith('/api/studio/scenes')) {
      return Promise.resolve({ ok: true, data: SCENES });
    }
    if (path.startsWith('/api/studio/list')) {
      return Promise.resolve({ ok: true, data: created ? [makeSession()] : [] });
    }
    if (path.startsWith('/api/studio/sess_1')) {
      return Promise.resolve({
        ok: true,
        data: {
          session: makeSession(),
          versions: [VERSION],
          messages: [],
          references: [{ asset_id: 'ref_1', description: 'такой свет' }],
        },
      });
    }
    if (path.includes('/art-direction/apply')) {
      return Promise.resolve({ ok: true, data: AD_APPLY });
    }
    if (path.includes('/art-direction/library')) {
      return Promise.resolve({ ok: true, data: AD_LIBRARY });
    }
    if (path.startsWith('/api/studio/art-direction')) {
      return Promise.resolve({ ok: true, data: AD });
    }
    if (path.startsWith('/book/assets?') && path.includes('asset_type=image')) {
      return Promise.resolve({ ok: true, data: [IMAGE_CURRENT, IMAGE_OUTDATED] });
    }
    if (path.startsWith('/book/assets?') && path.includes('asset_type=video')) {
      return Promise.resolve({ ok: true, data: [VIDEO_STALE_MOCK, VIDEO_REAL] });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);

  vi.mocked(api.post).mockImplementation(((path: string) => {
    if (path.startsWith('/api/studio/create')) {
      created = true;
      return Promise.resolve({ ok: true, data: { session: makeSession(), version: VERSION } });
    }
    return Promise.resolve({ ok: true, data: VERSION });
  }) as never);
}

async function renderStudio() {
  const { default: StudioPage } = await import('@/app/studio/page');
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <StudioPage />
    </QueryClientProvider>,
  );
}

async function openWorkspace() {
  await renderStudio();
  const createBtn = await screen.findByRole('button', { name: /Создать рабочую область сцены/ });
  fireEvent.click(createBtn);
  await screen.findByText('СИНОПСИС_1');
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  mockAuth();
  created = false;
  installApiMocks();
});

describe('Studio — режиссёрская область: шоты, просмотр, зависимости артефактов', () => {
  it('шоты: список, выбор плана, пошотовая правка через modify', async () => {
    await openWorkspace();

    // Список планов и провенанс источника
    expect(await screen.findByTestId('shot-item-0')).toBeTruthy();
    expect(screen.getByTestId('shot-item-1')).toBeTruthy();
    expect(screen.getByText('РЕЖИССЁРСКОЕ_УКАЗАНИЕ')).toBeTruthy();

    // По умолчанию выбран первый план
    const desc = screen.getByDisplayValue('ОПИСАНИЕ_0');
    fireEvent.change(desc, { target: { value: 'НОВОЕ_ОПИСАНИЕ_0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить описание плана' }));
    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        expect.stringContaining(
          '/api/studio/sess_1/modify?target=video_scenario&field_path=shots.0.description',
        ),
      );
    });

    // Выбор второго плана → его поля
    fireEvent.click(screen.getByTestId('shot-item-1'));
    expect(screen.getByDisplayValue('ОПИСАНИЕ_1')).toBeTruthy();
    expect(screen.getByDisplayValue('slow dolly in')).toBeTruthy();

    const cam = screen.getByDisplayValue('slow dolly in');
    fireEvent.change(cam, { target: { value: 'pan left' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить движение камеры' }));
    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        expect.stringContaining('field_path=shots.1.camera_action'),
      );
    });

    // Раздельность полей: предупреждение о независимости от утверждённых кадров
    expect(screen.getAllByText(/НЕ подменяет утверждённые изображения/).length).toBeGreaterThan(0);
  }, 60000);

  it('изображения: понятен выбранный вариант, просмотр в полный размер, теги промпта', async () => {
    await openWorkspace();

    // Теги соответствия текущему промпту у вариантов (асеты грузятся отдельным query)
    expect(await screen.findByText('по текущему промпту')).toBeTruthy();
    expect(await screen.findByText('прежний промпт')).toBeTruthy();
    expect(screen.getAllByText('по текущему промпту').length).toBe(1);

    // Открытие кадра в полном размере: prompt_used виден полностью
    const img = await screen.findByAltText('кадр: Гиперборея');
    fireEvent.click(img);
    expect(await screen.findByTestId('lightbox-image')).toBeTruthy();
    expect(screen.getByDisplayValue('КАДР_ПРОМПТ_1')).toBeTruthy();
  }, 60000);

  it('видео: mock-запись vs реальный клип, признак «потенциально устарело», параметры клипа', async () => {
    await openWorkspace();

    // Бейджи вида в списке видеоартефактов
    expect((await screen.findAllByText(/mock-запись \(без реального видео\)/)).length).toBeGreaterThan(0);
    expect(screen.getAllByText('реальный клип').length).toBeGreaterThan(0);

    // Зависимость: промпт движения изменился после генерации
    const stale = await screen.findAllByText('потенциально устарело');
    expect(stale.length).toBeGreaterThanOrEqual(1);
    expect(stale[0].getAttribute('title')).toContain('промпт движения изменился');

    // Параметры клипа и выбор разрешения в панели подготовки видео
    expect(screen.getByText(/Параметры клипа:/)).toBeTruthy();
    expect(screen.getAllByText(/длительность: 8 с/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/24 fps/).length).toBeGreaterThanOrEqual(1);
  }, 60000);

  it('референсы: вкладка, список и загрузка через FormData', async () => {
    await openWorkspace();

    // Существующий референс виден в списке
    fireEvent.click(screen.getByRole('button', { name: /Референсы/ }));
    expect(await screen.findByText('такой свет')).toBeTruthy();

    // Загрузка нового файла уходит FormData (без JSON)
    const input = screen.getByTestId('reference-file-input');
    const file = new File(['png'], 'ref.png', { type: 'image/png' });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        '/api/studio/sess_1/upload-reference',
        expect.any(FormData),
      );
    });
  }, 60000);
});


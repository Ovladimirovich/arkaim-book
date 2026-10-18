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

const VERSION = {
  version_id: 'ver_1',
  session_id: 'sess_1',
  version_number: 1,
  image_description: {
    plan_id: 'plan_img_1',
    prompt: 'КАДР_ПРОМПТ_1',
    negative_constraints: ['без текста'],
    media_kind: 'image',
  },
  video_description: {
    plan_id: 'plan_vid_1',
    prompt: 'ВИДЕО_ПРОМПТ_1',
    duration_sec: 8,
    fps: 24,
    motion: { camera_motion: 'slow_push_in' },
  },
  video_scenario: { scenario_id: 'sc_1', synopsis: 'СИНОПСИС_1', shots: [] },
  parent_version_id: null,
  derivation: 'initial',
  user_modifications: [],
  is_active: true,
  is_final: false,
  created_by: 'system',
  created_at: '2026-10-15T00:00:00',
  note: 'initial',
};

const makeSession = (approved: string | null) => ({
  session_id: 'sess_1',
  user_id: '1',
  title: 'тест',
  chapter: 1,
  scene_id: 'scene_1',
  context_type: 'scene',
  active_version_id: 'ver_1',
  status: 'draft',
  approved_image_asset_id: approved,
  reference_assets: [],
  created_at: '2026-10-15T00:00:00',
  updated_at: '2026-10-15T00:00:00',
  finalized_at: null,
});

const IMAGE_ASSET = {
  asset_id: 'asset_img_1',
  asset_type: 'image',
  chapter: 1,
  scene_id: 'scene_1',
  title: 'кадр: Гиперборея',
  status: 'completed',
  file_path: 'images/asset_img_1.png',
  error: null,
  generation: { provider: 'agnes', plan_id: 'plan_img_1' },
};

const EXISTING_VIDEO = {
  asset_id: 'asset_existing_1',
  asset_type: 'video',
  chapter: 1,
  scene_id: 'scene_1',
  title: 'Существующий клип',
  status: 'completed',
  file_path: 'videos/asset_existing_1.mp4',
  error: null,
  duration_sec: 8,
  generation: { provider: 'comfyicu', plan_id: 'plan_028a6dda3148', media_id: 'run_1' },
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
  revision: 1,
  updated_at: '2026-10-15T00:00:00',
  style_preset: 'cinematic_fantasy',
  style_prompt: '',
  palette: [],
  aspect_ratio: null,
  composition_rules: [],
  lighting_rules: [],
  negative_rules: [],
  characters: [],
  locations: [],
  reference_asset_ids: [],
  last_change_sections: [],
};

const AD_LIBRARY = {
  styles: {
    cinematic_fantasy: {
      prefix: 'cinematic fantasy film still',
      aspect_ratio: '16:9',
      description: 'кинематографическое фэнтези',
      negative_additions: [],
    },
  },
  characters: { Велик: { name: 'Велик' } },
  locations: { Гиперборея: { name: 'Гиперборея', type: 'city', palette: ['иней'] } },
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
    shot_count: 0,
    total_duration_sec: 0,
    style_label: 'cinematic_fantasy',
    revision: 1,
    last_change_sections: [],
  },
  shots: [],
  affected_artifacts: [],
};

/** Состояние, которое мутации меняют между запросами. */
let created = false;
let approvedId: string | null = null;
let imageAssets: Record<string, unknown>[] = [];
let videoAssets: Record<string, unknown>[] = [EXISTING_VIDEO];

function installApiMocks(opts: { videoJobAsset?: string } = {}) {
  const videoJobAsset = opts.videoJobAsset || 'asset_job_done';

  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.startsWith('/api/studio/film')) {
      return Promise.resolve({ ok: true, data: filmFromScenes(SCENES) });
    }
    if (path.startsWith('/api/studio/scenes')) {
      return Promise.resolve({ ok: true, data: SCENES });
    }
    if (path.startsWith('/api/studio/list')) {
      return Promise.resolve({ ok: true, data: created ? [makeSession(approvedId)] : [] });
    }
    if (path.startsWith('/api/studio/sess_1')) {
      return Promise.resolve({
        ok: true,
        data: {
          session: makeSession(approvedId),
          versions: [VERSION],
          messages: [],
          references: [],
        },
      });
    }
    if (path.startsWith('/book/assets/asset_job_done')) {
      return Promise.resolve({
        ok: true,
        data: {
          asset_id: 'asset_job_done',
          asset_type: 'video',
          chapter: 1,
          scene_id: 'scene_1',
          title: 'new job',
          status: 'completed',
          file_path: 'videos/asset_job_done.mp4',
          error: null,
          duration_sec: 8,
          generation: {
            provider: 'mock',
            backend: 'mock',
            plan_id: 'plan_vid_1',
            workflow_used: 'wflow_test',
            media_id: 'run_test_1',
            reference_image_id: approvedId,
            input_image_sha256: 'sha256_of_transmitted_frame',
          },
        },
      });
    }
    if (path.startsWith('/book/assets/asset_job_fail')) {
      return Promise.resolve({
        ok: true,
        data: {
          asset_id: 'asset_job_fail',
          asset_type: 'video',
          chapter: 1,
          scene_id: 'scene_1',
          title: 'failed job',
          status: 'failed',
          file_path: null,
          error: 'ComfyICU: HTTP 500',
        },
      });
    }
    if (path.startsWith('/book/assets/asset_job_noref')) {
      // completed БЕЗ reference_image_id: утверждённый кадр НЕ передавался
      return Promise.resolve({
        ok: true,
        data: {
          asset_id: 'asset_job_noref',
          asset_type: 'video',
          chapter: 1,
          scene_id: 'scene_1',
          title: 'видео без кадра',
          status: 'completed',
          file_path: 'videos/asset_job_noref.mp4',
          error: null,
          duration_sec: 8,
          generation: { provider: 'mock', backend: 'mock', plan_id: 'plan_vid_1' },
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
      return Promise.resolve({ ok: true, data: imageAssets });
    }
    if (path.startsWith('/book/assets?') && path.includes('asset_type=video')) {
      return Promise.resolve({ ok: true, data: videoAssets });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);

  vi.mocked(api.post).mockImplementation(((path: string) => {
    if (path.startsWith('/api/studio/create')) {
      created = true;
      return Promise.resolve({ ok: true, data: { session: makeSession(null), version: VERSION } });
    }
    if (path.startsWith('/api/studio/image-jobs')) {
      if (!imageAssets.some((a) => a.asset_id === IMAGE_ASSET.asset_id)) {
        imageAssets.push(IMAGE_ASSET);
      }
      return Promise.resolve({
        ok: true,
        data: { asset_id: 'asset_img_1', status: 'completed', scene_id: 'scene_1', plan_id: 'plan_img_1' },
      });
    }
    if (path.includes('/approve-image')) {
      approvedId = path.endsWith('asset_id=') ? null : 'asset_img_1';
      return Promise.resolve({ ok: true, data: { approved_image_asset_id: approvedId } });
    }
    if (path.startsWith('/api/studio/video-jobs')) {
      return Promise.resolve({
        ok: true,
        data: { asset_id: videoJobAsset, status: 'generating' },
      });
    }
    if (path.includes('/modify')) {
      return Promise.resolve({ ok: true, data: VERSION });
    }
    if (path.includes('/activate-version')) {
      return Promise.resolve({ ok: true, data: { activated: 'ver_1' } });
    }
    return Promise.resolve({ ok: true, data: null });
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
  approvedId = null;
  imageAssets = [];
  videoAssets = [EXISTING_VIDEO];
  installApiMocks();
});

describe('Studio — рабочая область: промпт → кадр → видео (offline)', () => {
  it('полный цикл: правка промпта, генерация и утверждение кадра, видео от кадра', async () => {
    await openWorkspace();

    // 1. Правка промпта сцены → modify
    const synopsis = screen.getByDisplayValue('СИНОПСИС_1');
    fireEvent.change(synopsis, { target: { value: 'НОВЫЙ_СИНОПСИС' } });
    fireEvent.click(screen.getByRole('button', { name: /Сохранить промпт/ }));
    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        expect.stringContaining('/api/studio/sess_1/modify?target=video_scenario&field_path=synopsis'),
      );
    });

    // 2. Вкладка «Промпт изображения» — промпт и negative
    fireEvent.click(screen.getByRole('button', { name: 'Промпт изображения' }));
    expect(screen.getByDisplayValue('КАДР_ПРОМПТ_1')).toBeTruthy();
    expect(screen.getByText('без текста')).toBeTruthy();

    // 3. Генерация варианта изображения (исполнитель agnes по умолчанию)
    fireEvent.click(screen.getByRole('button', { name: /Сгенерировать вариант/ }));
    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        '/api/studio/image-jobs',
        expect.objectContaining({
          chapter: 1,
          scene_id: 'scene_1',
          prompt: 'КАДР_ПРОМПТ_1',
          plan_id: 'plan_img_1',
          preferred_backend: 'agnes',
        }),
      );
    });

    // 4. Утверждение кадра → approved_image_asset_id в сессии
    const approveBtn = await screen.findByRole('button', { name: /Утвердить кадр/ });
    await waitFor(() => expect((approveBtn as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(approveBtn);
    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        expect.stringContaining('/api/studio/sess_1/approve-image?asset_id=asset_img_1'),
      );
    });
    await screen.findByText(/выбрано для видео/);
    expect(screen.getByText(/Кадр утверждён/)).toBeTruthy();

    // 5. Видео создаётся от утверждённого кадра
    const videoBtn = screen.getByRole('button', { name: /Создать видео/ });
    await waitFor(() => expect((videoBtn as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(videoBtn);
    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        '/api/studio/video-jobs',
        expect.objectContaining({
          chapter: 1,
          scene_id: 'scene_1',
          prompt: 'ВИДЕО_ПРОМПТ_1. движение камеры: slow_push_in',
          plan_id: 'plan_vid_1',
          preferred_backend: 'mock',
          image_asset_id: 'asset_img_1',
        }),
      );
    });

    // 6. Статусная панель: готово + провенанс (кадр ФАКТИЧЕСКИ передан исполнителю)
    await screen.findByText(/Видео готово/, undefined, { timeout: 8000 });
    expect(screen.getByText(/кадр передан: asset_img_1/)).toBeTruthy();
    expect(screen.getByText(/sha256: sha256_of/)).toBeTruthy();
    expect(screen.getByText(/исполнитель: mock/)).toBeTruthy();
  }, 20000);

  it('видео запускается и без кадра, но показывается предупреждение; ошибка видна текстом', async () => {
    installApiMocks({ videoJobAsset: 'asset_job_fail' });
    await openWorkspace();

    // Кадр не утверждён — предупреждение в панели видео
    expect(await screen.findByText('Кадр не утверждён')).toBeTruthy();

    const videoBtn = screen.getByRole('button', { name: /Создать видео/ });
    await waitFor(() => expect((videoBtn as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(videoBtn);

    await screen.findByText(/Задание завершилось ошибкой/, undefined, { timeout: 8000 });
    expect(screen.getByText(/ComfyICU: HTTP 500/)).toBeTruthy();
    expect(document.body.innerHTML).not.toContain('/book/assets/asset_job_fail/file');
  }, 20000);

  it('различает утверждённый кадр и фактически переданный: предупреждение, если кадр не дошёл', async () => {
    await openWorkspace();

    // Утверждаем кадр (image-jobs → approve-image)
    fireEvent.click(screen.getByRole('button', { name: /Сгенерировать вариант/ }));
    await waitFor(() => expect(vi.mocked(api.post)).toHaveBeenCalledWith('/api/studio/image-jobs', expect.anything()));
    const approveBtn = await screen.findByRole('button', { name: /Утвердить кадр/ });
    await waitFor(() => expect((approveBtn as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(approveBtn);
    await screen.findByText(/Кадр утверждён/);

    // Задание видео завершилось БЕЗ reference_image_id (кадр не передавался)
    installApiMocks({ videoJobAsset: 'asset_job_noref' });
    videoAssets = [
      {
        asset_id: 'asset_job_noref',
        asset_type: 'video',
        chapter: 1,
        scene_id: 'scene_1',
        title: 'видео без кадра',
        status: 'completed',
        file_path: 'videos/asset_job_noref.mp4',
        error: null,
        duration_sec: 8,
        generation: { provider: 'mock', backend: 'mock', plan_id: 'plan_vid_1' },
      },
    ];

    const videoBtn = screen.getByRole('button', { name: /Создать видео/ });
    await waitFor(() => expect((videoBtn as HTMLButtonElement).disabled).toBe(false));
    fireEvent.click(videoBtn);

    // Утверждённый кадр был, но фактически не передан → явное предупреждение
    await screen.findByText(/Визуальная связь не гарантирована/, undefined, { timeout: 8000 });
    expect(screen.getByText(/НЕ передавался исполнителю/)).toBeTruthy();
    // В списке артефактов — тег «без кадра-основы»
    expect(screen.getByText(/без кадра-основы \(утверждённый не передавался\)/)).toBeTruthy();
    // Утверждённый кадр при этом всё ещё показывается в своей секции
    expect(screen.getAllByText('asset_img_1').length).toBeGreaterThan(0);
  }, 20000);

  it('пустое состояние: нет сцен — подсказка выбрать сцену', async () => {
    vi.mocked(api.get).mockImplementation(((path: string) => {
      if (path.startsWith('/api/studio/scenes')) {
        return Promise.resolve({ ok: true, data: [] });
      }
      return Promise.resolve({ ok: true, data: [] });
    }) as never);

    await renderStudio();

    expect(await screen.findByText(/Выберите сцену книги/)).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Создать рабочую область сцены/ })).toBeNull();
  }, 15000);
});

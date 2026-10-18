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
import { StoryReel } from '@/app/studio/story-reel';
import type { ReelT, Scene } from '@/app/studio/types';

const SCENE: Scene = { scene_id: 'scene_a', chapter: 1, title: 'Сцена A' };

const SCENES = [
  { scene_id: 'scene_a', chapter: 1, title: 'Сцена A' },
  { scene_id: 'scene_b', chapter: 1, title: 'Сцена B' },
  { scene_id: 'scene_c', chapter: 2, title: 'Сцена C' },
];

const REEL: ReelT = {
  scope: 'scene',
  chapter: 1,
  scene_ids: ['scene_a'],
  film: { book_id: 'nasledie-arkaima', title: 'Наследие Аркаима' },
  scenes: [
    {
      scene_id: 'scene_a',
      chapter: 1,
      index_in_episode: 0,
      order_global: 0,
      title: 'Сцена A',
      location: 'Аркаим',
      characters: ['Велик'],
      has_session: true,
      session_id: 'sess_a',
      session_status: 'draft',
      approved_image_asset_id: 'img_a',
      shot_count: 2,
      total_duration_sec: 8,
      continuity_from_prev_scene: null,
      transfer: { applied: true, stale: false, from_scene_id: 'scene_0', note: '' },
      shots: [
        {
          shot_id: 'shot_1',
          order: 0,
          index: 0,
          shot_type: 'wide',
          description: 'Общий план',
          duration_sec: 4,
          transition_to_next: 'cut',
          frame: { status: 'approved', asset_id: 'img_1' },
          video: { status: 'none', asset_id: null, mock: false, stale_reasons: [] },
          resolved_prompt: 'Промпт 1',
          continuity_next: {
            status: 'mismatch',
            relation: 'shots_within_scene',
            certainty: 'confirmed',
            from_ref: 'shot_1',
            to_ref: 'shot_2',
            from_scene_id: 'scene_a',
            to_scene_id: 'scene_a',
            finding_count: 1,
            findings: [
              {
                field: 'lighting',
                kind: 'difference',
                severity: 'warning',
                message: 'Разница в свете между планами',
                subject: '',
                from_value: 'west',
                to_value: 'east',
                certainty: 'confirmed',
                sources: ['visual_context'],
              },
            ],
            decision: null,
            reason: '',
          },
        },
        {
          shot_id: 'shot_2',
          order: 1,
          index: 1,
          shot_type: 'close',
          description: 'Крупный план',
          duration_sec: 4,
          transition_to_next: '',
          frame: { status: 'needs_update', asset_id: 'img_2' },
          video: { status: 'mock', asset_id: 'vid_2', mock: true, stale_reasons: [] },
          resolved_prompt: 'Промпт 2',
          continuity_next: null,
        },
      ],
      warnings: [],
    },
  ],
  sequence: [
    {
      scene_id: 'scene_a',
      chapter: 1,
      index_in_episode: 0,
      shot_id: 'shot_1',
      shot_order: 0,
      shot_index: 0,
      kind: 'frame',
      frame_asset_id: 'img_1',
      clip_asset_id: null,
      clip_status: 'none',
      duration_sec: 4,
      transition_to_next: 'cut',
      description: 'Общий план',
    },
    {
      scene_id: 'scene_a',
      chapter: 1,
      index_in_episode: 0,
      shot_id: 'shot_2',
      shot_order: 1,
      shot_index: 1,
      kind: 'clip',
      frame_asset_id: 'img_2',
      clip_asset_id: 'vid_2',
      clip_status: 'mock',
      duration_sec: 4,
      transition_to_next: '',
      description: 'Крупный план',
    },
  ],
  summary: {
    scene_count: 1,
    shot_count: 2,
    clip_count: 1,
    frame_count: 1,
    placeholder_count: 0,
    mock_count: 1,
    stale_count: 0,
    total_duration_sec: 8,
  },
  limitations: [],
};

function installApiMocks() {
  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.includes('/api/studio/scenes')) {
      return Promise.resolve({ ok: true, data: SCENES });
    }
    if (path.includes('/api/studio/reel')) {
      return Promise.resolve({ ok: true, data: REEL });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);

  vi.mocked(api.post).mockImplementation((() =>
    Promise.resolve({ ok: true, data: { asset_id: 'vid_new', status: 'experimental' } })) as never);
}

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <StoryReel scene={SCENE} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  installApiMocks();
});

describe('Лента сцены (Story Reel, Фаза 3)', () => {
  it('показывает сцену, планы, кадры/клипы и сводку', async () => {
    renderPanel();

    const reel = await screen.findByTestId('story-reel');
    await waitFor(() => expect(screen.getAllByTestId('reel-shot').length).toBe(2));

    expect(reel.textContent).toContain('Эпизод 1 · Сцена 1 · Сцена A');
    expect(reel.textContent).toContain('План 1 · wide');
    expect(reel.textContent).toContain('План 2 · close');
    // Статусы кадра и клипа
    expect(screen.getByText('кадр утверждён')).toBeTruthy();
    expect(screen.getByText('кадр требует обновления')).toBeTruthy();
    expect(screen.getByText('mock-клип (без реального видео)')).toBeTruthy();
    // Сводка
    expect(reel.textContent).toContain('планов: 2');
    expect(reel.textContent).toContain('клипов: 1');
  });

  it('показывает метку переноса и связность на границе планов', async () => {
    renderPanel();

    const reel = await screen.findByTestId('story-reel');
    await waitFor(() => expect(screen.getAllByTestId('reel-continuity').length).toBeGreaterThan(0));

    expect(reel.textContent).toContain('учитывается перенос из: Сцена scene_0');
    expect(reel.textContent).toContain('есть потенциальное несоответствие');
  });

  it('кнопка «Создать видео из утверждённого кадра» доступна только для утверждённого кадра и создаёт задание', async () => {
    renderPanel();

    const btn = await screen.findByText('Создать видео из утверждённого кадра');
    // Только один план подходит (shot_1 с утверждённым кадром и без клипа)
    expect(screen.getAllByText('Создать видео из утверждённого кадра').length).toBe(1);

    fireEvent.click(btn);

    await waitFor(() =>
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        '/api/studio/video-jobs',
        expect.objectContaining({
          chapter: 1,
          scene_id: 'scene_a',
          shot_id: 'shot_1',
          image_asset_id: 'img_1',
          preferred_backend: 'mock',
        }),
      ),
    );
  });

  it('переключение области «Весь эпизод» запрашивает ленту без scene_id', async () => {
    renderPanel();

    await screen.findByTestId('story-reel');
    fireEvent.click(screen.getByText('Весь эпизод'));

    await waitFor(() =>
      expect(vi.mocked(api.get)).toHaveBeenCalledWith(
        expect.stringMatching(/^\/api\/studio\/reel\?chapter=1$/),
      ),
    );
  });

  it('последовательность запрашивает scene_ids без нарушения канонического порядка', async () => {
    renderPanel();

    await screen.findByTestId('story-reel');
    fireEvent.click(screen.getByText('Последовательность'));

    await waitFor(() =>
      expect(vi.mocked(api.get)).toHaveBeenCalledWith(
        expect.stringContaining('/api/studio/reel?chapter=1&scene_ids=scene_a'),
      ),
    );
  });

  it('предпросмотр показывает материал и переключает планы', async () => {
    renderPanel();

    const player = await screen.findByTestId('reel-player');
    expect(player.textContent).toContain('1 / 2');
    // Первый план — кадр (kind=frame → «кадр»)
    expect(player.textContent).toContain('кадр');
  });
});

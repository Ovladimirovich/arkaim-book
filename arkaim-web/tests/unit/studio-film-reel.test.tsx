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
import { FilmReel } from '@/app/studio/film-reel';
import type { ReelLinkT, ReelShotT, ReelT } from '@/app/studio/types';

function shot(partial: Partial<ReelShotT> & Pick<ReelShotT, 'shot_id' | 'index'>): ReelShotT {
  return {
    order: partial.index,
    shot_type: 'medium',
    description: '',
    duration_sec: 3,
    transition_to_next: '',
    frame: { status: 'none', asset_id: null },
    video: { status: 'none', asset_id: null, mock: false, stale_reasons: [] },
    resolved_prompt: '',
    continuity_next: null,
    ...partial,
  };
}

const LINK: ReelLinkT = {
  status: 'mismatch',
  relation: 'scene_boundary_shots',
  certainty: 'confirmed',
  from_ref: 'shot_a1',
  to_ref: 'shot_b1',
  from_scene_id: 'scene_a',
  to_scene_id: 'scene_b',
  finding_count: 1,
  findings: [],
  decision: null,
  reason: '',
};

const REEL: ReelT = {
  scope: 'film',
  chapter: null,
  scene_ids: ['scene_a', 'scene_b', 'scene_c'],
  film: { book_id: 'nasledie-arkaima', title: 'Наследие Аркаима', episode_count: 2 },
  scenes: [
    {
      scene_id: 'scene_a',
      chapter: 1,
      index_in_episode: 0,
      order_global: 0,
      title: 'Сцена A',
      location: 'Аркаим',
      characters: [],
      has_session: true,
      session_id: 'sess_a',
      session_status: 'draft',
      approved_image_asset_id: null,
      shot_count: 1,
      total_duration_sec: 3,
      continuity_from_prev_scene: null,
      transfer: { applied: true, stale: false, from_scene_id: 'scene_0', note: '' },
      warnings: [],
      shots: [
        shot({
          shot_id: 'shot_a1',
          index: 0,
          frame: { status: 'none', asset_id: 'img_a1' },
          video: { status: 'mock', asset_id: 'vid_a1', mock: true, stale_reasons: [] },
          continuity_next: LINK,
        }),
      ],
    },
    {
      scene_id: 'scene_b',
      chapter: 1,
      index_in_episode: 1,
      order_global: 1,
      title: 'Сцена B',
      location: 'Лес',
      characters: [],
      has_session: false,
      session_id: null,
      session_status: null,
      approved_image_asset_id: null,
      shot_count: 1,
      total_duration_sec: 3,
      continuity_from_prev_scene: null,
      transfer: null,
      warnings: [],
      shots: [shot({ shot_id: 'shot_b1', index: 0, frame: { status: 'needs_update', asset_id: 'img_b1' } })],
    },
    {
      scene_id: 'scene_c',
      chapter: 2,
      index_in_episode: 0,
      order_global: 2,
      title: 'Сцена C',
      location: '',
      characters: [],
      has_session: true,
      session_id: 'sess_c',
      session_status: 'draft',
      approved_image_asset_id: null,
      shot_count: 1,
      total_duration_sec: 3,
      continuity_from_prev_scene: null,
      transfer: null,
      warnings: [],
      shots: [shot({ shot_id: 'shot_c1', index: 0 })],
    },
  ],
  sequence: [
    {
      scene_id: 'scene_a',
      chapter: 1,
      index_in_episode: 0,
      shot_id: 'shot_a1',
      shot_order: 0,
      shot_index: 0,
      kind: 'clip',
      frame_asset_id: 'img_a1',
      clip_asset_id: 'vid_a1',
      clip_status: 'mock',
      duration_sec: 3,
      transition_to_next: '',
      description: '',
    },
    {
      scene_id: 'scene_c',
      chapter: 2,
      index_in_episode: 0,
      shot_id: 'shot_c1',
      shot_order: 0,
      shot_index: 0,
      kind: 'placeholder',
      frame_asset_id: null,
      clip_asset_id: null,
      clip_status: 'none',
      duration_sec: 3,
      transition_to_next: '',
      description: '',
    },
  ],
  summary: {
    scene_count: 3,
    shot_count: 3,
    clip_count: 1,
    frame_count: 1,
    placeholder_count: 1,
    mock_count: 1,
    stale_count: 0,
    total_duration_sec: 9,
  },
  limitations: [],
};

function installApiMocks(reel: unknown = REEL) {
  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.includes('/api/studio/reel')) {
      return Promise.resolve({ ok: true, data: reel });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);
}

function renderReel(onOpenScene = vi.fn(), selectedKey: string | null = null) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <FilmReel onOpenScene={onOpenScene} selectedKey={selectedKey} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  installApiMocks();
});

describe('Лента фильма (Film Reel, независимо от сессии)', () => {
  it('показывает сводку всего фильма и группирует сцены по эпизодам', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    expect(reel.textContent).toContain('эпизодов: 2');
    expect(reel.textContent).toContain('сцен: 3');
    expect(reel.textContent).toContain('планов: 3');
    expect(reel.textContent).toContain('клипов: 1');
    // Два эпизода (глава 1 и глава 2), сцены из разных глав.
    const episodes = screen.getAllByTestId('film-reel-episode');
    expect(episodes.length).toBe(2);
    expect(reel.textContent).toContain('Эпизод 1');
    expect(reel.textContent).toContain('Эпизод 2');
    expect(reel.textContent).toContain('Сцена A');
    expect(reel.textContent).toContain('Сцена C');
  });

  it('показывает состояние кадров/клипов, статусы сцены и перенос', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-shot').length).toBe(3));

    expect(reel.textContent).toContain('mock-клип (без реального видео)');
    expect(reel.textContent).toContain('кадр требует обновления');
    expect(reel.textContent).toContain('нет рабочей области'); // scene_b без сессии
    expect(reel.textContent).toContain('перенос из: scene_0');
    expect(reel.textContent).toContain('есть потенциальное несоответствие'); // boundary continuity
  });

  it('«Открыть в Studio» возвращает сцену и главу для навигации', async () => {
    const onOpenScene = vi.fn();
    renderReel(onOpenScene);

    await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByText('Открыть в Studio').length).toBe(3));

    fireEvent.click(screen.getAllByText('Открыть в Studio')[1]);
    expect(onOpenScene).toHaveBeenCalledWith({ scene_id: 'scene_b', chapter: 1 });
  });

  it('предпросмотр всего фильма использует полную последовательность', async () => {
    renderReel();

    const player = await screen.findByTestId('reel-player');
    expect(player.textContent).toContain('1 / 2');
  });

  it('устойчива к пустому/чужому ответу сервера', async () => {
    installApiMocks([]);
    renderReel();

    await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getByText('Сцены книги не найдены.')).toBeTruthy());
  });
});

function clickFilter(testid: string) {
  const chip = screen.getByTestId(testid);
  const button = chip.querySelector('button');
  expect(button).toBeTruthy();
  fireEvent.click(button as HTMLButtonElement);
}

describe('Лента фильма: фильтр и поиск', () => {
  it('текстовый поиск по сцене сужает показ и пересчитывает сводку', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    fireEvent.change(screen.getByPlaceholderText(/Поиск:/), { target: { value: 'Лес' } });

    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(1));
    expect(reel.textContent).toContain('Сцена B');
    expect(screen.getByTestId('film-reel-filtered-note').textContent).toContain('показано сцен: 1 из 3');
  });

  it('текстовый поиск по плану показывает только совпавшие планы', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    fireEvent.change(screen.getByPlaceholderText(/Поиск:/), { target: { value: 'shot_c1' } });

    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(1));
    expect(reel.textContent).toContain('Сцена C');
    expect(screen.getAllByTestId('film-reel-shot').length).toBe(1);
  });

  it('фильтр «Mock» оставляет только сцены с mock-клипом', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    clickFilter('film-reel-status-filter-mock');

    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(1));
    expect(reel.textContent).toContain('Сцена A');
  });

  it('фильтр «Без рабочей области» оставляет только сцены без сессии', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    clickFilter('film-reel-status-filter-no_session');

    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(1));
    expect(reel.textContent).toContain('Сцена B');
  });

  it('фильтр «Несоответствие» оставляет сцены с расхождением связности', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    clickFilter('film-reel-status-filter-continuity');

    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(1));
    expect(reel.textContent).toContain('Сцена A');
  });

  it('фильтр по эпизоду показывает только сцены этого эпизода', async () => {
    renderReel();

    const reel = await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    clickFilter('film-reel-episode-filter-1');

    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(2));
    expect(reel.textContent).toContain('Сцена A');
    expect(reel.textContent).toContain('Сцена B');
    expect(reel.textContent).not.toContain('Сцена C');
  });

  it('пустой результат фильтра показывает сообщение', async () => {
    renderReel();

    await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    fireEvent.change(screen.getByPlaceholderText(/Поиск:/), { target: { value: 'нет-такого-xyz' } });

    await waitFor(() => expect(screen.getByText('Ничего не найдено по фильтру.')).toBeTruthy());
    expect(screen.queryAllByTestId('film-reel-scene').length).toBe(0);
  });

  it('«Сбросить фильтр» возвращает полную ленту', async () => {
    renderReel();

    await screen.findByTestId('film-reel');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));

    clickFilter('film-reel-status-filter-mock');
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(1));

    fireEvent.click(screen.getByText('Сбросить фильтр'));
    await waitFor(() => expect(screen.getAllByTestId('film-reel-scene').length).toBe(3));
  });
});

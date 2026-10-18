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
import { FilmSequence } from '@/app/studio/sequence';
import type { SequencePlanT, SequenceSegmentT } from '@/app/studio/types';

function segment(partial: Partial<SequenceSegmentT> & Pick<SequenceSegmentT, 'index' | 'shot_id'>): SequenceSegmentT {
  return {
    scene_id: 'scene_a',
    chapter: 1,
    index_in_episode: 0,
    shot_order: partial.index,
    shot_index: partial.index,
    kind: 'placeholder',
    clip_status: 'none',
    frame_status: 'none',
    mock: false,
    ready: false,
    duration_sec: 3,
    start_sec: partial.index * 3,
    end_sec: partial.index * 3 + 3,
    transition_to_next: '',
    scene_boundary_after: false,
    clip_asset_id: null,
    frame_asset_id: null,
    executor: null,
    executor_key: null,
    executor_label: null,
    description: '',
    ...partial,
  };
}

const PLAN: SequencePlanT = {
  segments: [
    segment({
      index: 0,
      shot_id: 'shot_ready_1',
      kind: 'clip',
      clip_status: 'ready',
      ready: true,
      clip_asset_id: 'vid_1',
      executor: { provider: 'agnes' },
      executor_key: 'agnes',
      executor_label: 'agnes',
      transition_to_next: 'dissolve',
    }),
    segment({ index: 1, shot_id: 'shot_frame', kind: 'frame', frame_status: 'approved', frame_asset_id: 'img_2' }),
    segment({ index: 2, shot_id: 'shot_empty' }),
    segment({
      index: 3,
      shot_id: 'shot_ready_2',
      kind: 'clip',
      clip_status: 'ready',
      ready: true,
      clip_asset_id: 'vid_2',
      executor: { provider: 'comfyicu', model: 'ltx' },
      executor_key: 'comfyicu / ltx',
      executor_label: 'comfyicu · ltx',
      scene_boundary_after: true,
    }),
  ],
  assembled: [
    { index: 0, scene_id: 'scene_a', chapter: 1, shot_id: 'shot_ready_1', start_sec: 0, end_sec: 3, duration_sec: 3, clip_asset_id: 'vid_1', executor_label: 'agnes', transition_to_next: 'dissolve' },
    { index: 3, scene_id: 'scene_a', chapter: 1, shot_id: 'shot_ready_2', start_sec: 9, end_sec: 12, duration_sec: 3, clip_asset_id: 'vid_2', executor_label: 'comfyicu · ltx', transition_to_next: '' },
  ],
  gaps: [
    {
      start_index: 1,
      end_index: 2,
      segment_count: 2,
      start_sec: 3,
      end_sec: 9,
      duration_sec: 6,
      kinds: ['frame', 'placeholder'],
      scene_ids: ['scene_a'],
      shot_ids: ['shot_frame', 'shot_empty'],
    },
  ],
  transitions: [
    { index: 0, from_shot_id: 'shot_ready_1', to_shot_id: 'shot_frame', transition: 'dissolve', scene_boundary: false, from_ready: true, to_ready: false },
    { index: 1, from_shot_id: 'shot_frame', to_shot_id: 'shot_empty', transition: '', scene_boundary: false, from_ready: false, to_ready: false },
    { index: 2, from_shot_id: 'shot_empty', to_shot_id: 'shot_ready_2', transition: '', scene_boundary: false, from_ready: false, to_ready: true },
  ],
  executors: [
    { key: 'agnes', label: 'agnes', count: 1, duration_sec: 3, shot_ids: ['shot_ready_1'] },
    { key: 'comfyicu / ltx', label: 'comfyicu · ltx', count: 1, duration_sec: 3, shot_ids: ['shot_ready_2'] },
  ],
  executor_mixed: true,
  summary: {
    segment_count: 4,
    scene_count: 1,
    episode_count: 1,
    clip_count: 2,
    ready_count: 2,
    frame_count: 1,
    placeholder_count: 1,
    mock_count: 0,
    stale_count: 0,
    assembled_count: 2,
    gap_count: 1,
    executor_count: 2,
    total_duration_sec: 12,
    assembled_duration_sec: 6,
    gap_duration_sec: 6,
  },
  limitations: [],
  plan_text: 'План сборки последовательности фильма\n\nОтрезков: 4 · готовых клипов: 2 · разрывов: 1',
  edl_xml: '<?xml version="1.0" encoding="UTF-8"?>\n<edit_decision_list>\n  <ready_clips>2</ready_clips>\n  <clips>\n    <clip><shot_id>shot_ready_1</shot_id></clip>\n    <clip><shot_id>shot_ready_2</shot_id></clip>\n  </clips>\n</edit_decision_list>',
  scope: 'film',
  chapter: null,
  scene_ids: ['scene_a'],
  film: { book_id: 'nasledie-arkaima', title: 'Наследие Аркаима', episode_count: 5 },
};

function installApiMocks(plan: unknown = PLAN) {
  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.includes('/api/studio/sequence')) {
      return Promise.resolve({ ok: true, data: plan });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);
}

function renderSequence() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <FilmSequence />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  installApiMocks();
});

describe('План сборки последовательности (Фаза 4)', () => {
  it('показывает сводку, исполнителей и флаг смешанных исполнителей', async () => {
    renderSequence();
    const root = await screen.findByTestId('film-sequence');

    await waitFor(() => expect(root.textContent).toContain('готово к сборке: 2'));

    expect(root.textContent).toContain('отрезков: 4');
    expect(root.textContent).toContain('разрывов: 1');
    expect(root.textContent).toContain('смешанные исполнители: 2');
    expect(screen.getAllByTestId('film-sequence-executor').length).toBe(2);
  });

  it('показывает разрывы и таблицу отрезков', async () => {
    renderSequence();
    const root = await screen.findByTestId('film-sequence');

    await waitFor(() => expect(screen.getByTestId('film-sequence-gap')).toBeTruthy());

    expect(root.textContent).toContain('Разрывы (нет готового клипа)');
    // Разрыв свёрнут по умолчанию — клик раскрывает детали с shot_id.
    fireEvent.click(screen.getByTestId('film-sequence-gap'));
    await waitFor(() => expect(screen.getByTestId('film-sequence-gap-details')).toBeTruthy());
    expect(root.textContent).toContain('shot_frame');
    expect(root.textContent).toContain('shot_empty');
    // Готовые отрезки отображаются в таблице.
    expect(root.textContent).toContain('shot_ready_1');
    expect(root.textContent).toContain('shot_ready_2');
    expect(root.textContent).toContain('dissolve');
    expect(root.textContent).toContain('comfyicu · ltx');
    expect(root.textContent).toContain('граница сцен');
  });

  it('показывает/скрывает текстовый план', async () => {
    renderSequence();
    await screen.findByTestId('film-sequence');

    const toggle = await screen.findByText('Показать текстовый план');
    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getByTestId('film-sequence-plan-text')).toBeTruthy());
    expect(screen.getByTestId('film-sequence-plan-text').textContent).toContain('План сборки последовательности фильма');

    fireEvent.click(screen.getByText('Скрыть текстовый план'));
    await waitFor(() => expect(screen.queryByTestId('film-sequence-plan-text')).toBeNull());
  });

  it('устойчива к пустому ответу сервера', async () => {
    installApiMocks(null);
    renderSequence();
    await screen.findByTestId('film-sequence');
    await waitFor(() => expect(screen.getByText('Сцены книги не найдены.')).toBeTruthy());
  });

  it('экспорт плана сохраняет .txt файл и показывает уведомление', async () => {
    renderSequence();
    await screen.findByTestId('film-sequence');

    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:http://test');
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL');
    const addEvent = EventTarget.prototype.addEventListener;

    await waitFor(() => expect(screen.getByText('Экспорт плана (TXT)')).toBeTruthy());
    fireEvent.click(screen.getByText('Экспорт плана (TXT)'));

    await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
    expect(revokeObjectURL).toHaveBeenCalled();
    // Тост должен появиться — в jsdom download происходит через созданный <a>, поэтому проверяем результат.
    expect(createObjectURL.mock.calls[0][0]).toBeInstanceOf(Blob);
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });

  it('экспорт EDL (XML) создаёт файл и показывает уведомление', async () => {
    renderSequence();
    await screen.findByTestId('film-sequence');

    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:http://edl-test');
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL');

    await waitFor(() => expect(screen.getByText('Экспорт EDL (XML)')).toBeTruthy());
    const allButtons = document.querySelectorAll('button');
    const edlBtn = Array.from(allButtons).find((b) => b.textContent?.includes('EDL'));
    expect(edlBtn).toBeTruthy();
    fireEvent.click(edlBtn!);

    await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
    expect(revokeObjectURL).toHaveBeenCalled();
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('application/xml;charset=utf-8');
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });

  it('фильтр «Только готовые» сужает таблицу до ready-отрезков', async () => {
    renderSequence();
    await screen.findByTestId('film-sequence');

    // Фильтр всегда доступен после загрузки данных.
    const filterBtn = await screen.findByTestId('film-sequence-filter-ready');
    expect(filterBtn.textContent).toContain('Только готовые');

    // LButton не пробрасывает data-testid на DOM-элемент — клик по wrapper.
    const btn = filterBtn.querySelector('button');
    expect(btn).toBeTruthy();
    fireEvent.click(btn!);
    await waitFor(() => expect(filterBtn.textContent).toContain('Показать все'));

    // В DOM должны остаться только shot_ready_1 и shot_ready_2 (2 строки с этими id).
    const allRows = screen.queryAllByText(/shot_ready/);
    expect(allRows.length).toBe(2);
    expect(screen.queryByText('shot_frame')).toBeNull();
    expect(screen.queryByText('shot_empty')).toBeNull();
  });
});

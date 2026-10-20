import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';

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

import { FilmTree } from '@/app/studio/film-tree';
import { scenesFromFilm } from '@/app/studio/types';
import type { FilmT } from '@/app/studio/types';

const FILM: FilmT = {
  film: {
    book_id: 'nasledie-arkaima',
    title: 'Наследие Аркаима',
    episode_count: 2,
    scene_count: 3,
    total_duration_sec: 21,
  },
  episodes: [
    {
      episode_id: 'chapter_1',
      chapter: 1,
      title: 'Глава 1',
      scene_count: 2,
      total_duration_sec: 18,
      scenes: [
        {
          scene_id: 'scene_a',
          chapter: 1,
          index_in_episode: 0,
          order_global: 0,
          title: 'Сцена A',
          location: 'город',
          characters: ['Велик'],
          emotion: 'тревога',
          visual_style_hint: 'contrast',
          world_link_counts: { confirmed: 2, derived: 7, unresolved: 1 },
          has_session: true,
          session_id: 'sess_a',
          session_status: 'draft',
          approved_image_asset_id: 'img_a',
          shot_count: 3,
          total_duration_sec: 18,
          video_count: 1,
          has_video: true,
          status: 'video',
          shots: [],
        },
        {
          scene_id: 'scene_b',
          chapter: 1,
          index_in_episode: 1,
          order_global: 1,
          title: 'Сцена B',
          location: 'лес',
          characters: [],
          emotion: 'спокойствие',
          visual_style_hint: '',
          world_link_counts: { confirmed: 0, derived: 5, unresolved: 1 },
          has_session: false,
          session_id: null,
          session_status: null,
          approved_image_asset_id: null,
          shot_count: 0,
          total_duration_sec: 0,
          video_count: 0,
          has_video: false,
          status: 'no_session',
          shots: [],
        },
      ],
    },
    {
      episode_id: 'chapter_2',
      chapter: 2,
      title: 'Глава 2',
      scene_count: 1,
      total_duration_sec: 3,
      scenes: [
        {
          scene_id: 'scene_c',
          chapter: 2,
          index_in_episode: 0,
          order_global: 2,
          title: 'Сцена C',
          location: '',
          characters: [],
          emotion: '',
          visual_style_hint: '',
          world_link_counts: { confirmed: 0, derived: 0, unresolved: 1 },
          has_session: true,
          session_id: 'sess_c',
          session_status: 'draft',
          approved_image_asset_id: null,
          shot_count: 1,
          total_duration_sec: 3,
          video_count: 0,
          has_video: false,
          status: 'prompts',
          shots: [],
        },
      ],
    },
  ],
};

beforeEach(() => cleanup());

describe('FilmTree — дерево фильма (эпизод → сцена)', () => {
  it('показывает эпизоды и сцены с агрегатами', () => {
    render(<FilmTree film={FILM} selectedKey={null} onSelect={vi.fn()} />);

    expect(screen.getByTestId('film-tree')).toBeTruthy();
    expect(screen.getByText('Глава 1')).toBeTruthy();
    expect(screen.getByText('Глава 2')).toBeTruthy();
    expect(screen.getByText('Сцена A')).toBeTruthy();
    expect(screen.getByText('Сцена C')).toBeTruthy();
    // Итог по фильму: 2 эпизода, 3 сцены
    expect(screen.getByText(/2 эпизод/)).toBeTruthy();
    expect(screen.getByText(/3 сцен/)).toBeTruthy();
  });

  it('показывает статус сцены и наличие видео', () => {
    render(<FilmTree film={FILM} selectedKey={null} onSelect={vi.fn()} />);

    expect(screen.getByText('видео')).toBeTruthy(); // scene_a: video
    expect(screen.getByText('промпты')).toBeTruthy(); // scene_c: prompts
    expect(screen.getByText('нет рабочей области')).toBeTruthy(); // scene_b: no_session
    expect(screen.getByText('видео: 1')).toBeTruthy(); // счётчик видео-ассетов
  });

  it('показывает бейдж связей с миром и подсказку с полной картиной', () => {
    render(<FilmTree film={FILM} selectedKey={null} onSelect={vi.fn()} />);

    // scene_a: 2 подтверждённые и 7 производных
    expect(screen.getByText('мир 2/7')).toBeTruthy();
    // scene_b: только производные — отдельное число
    expect(screen.getByText('мир 5')).toBeTruthy();
    // scene_c: разрешённых связей нет — бейдж не показывается
    expect(screen.queryByText('мир 0')).toBeNull();

    const badge = screen.getByText('мир 2/7');
    expect(badge.getAttribute('title')).toContain('подтверждено 2');
    expect(badge.getAttribute('title')).toContain('производных 7');
    expect(badge.getAttribute('title')).toContain('без данных 1');
  });

  it('печатает сводку по связям с миром в шапке дерева', () => {
    render(<FilmTree film={FILM} selectedKey={null} onSelect={vi.fn()} />);

    expect(screen.getByText(/Мир: 1 сцен подтверждено/)).toBeTruthy();
    expect(screen.getByText(/1 только производные/)).toBeTruthy();
    expect(screen.getByText(/1 без связей/)).toBeTruthy();
  });

  it('клик по сцене возвращает ключ chapter:scene_id', () => {
    const onSelect = vi.fn();
    render(<FilmTree film={FILM} selectedKey={null} onSelect={onSelect} />);

    fireEvent.click(screen.getByText('Сцена A'));
    expect(onSelect).toHaveBeenCalledWith('1:scene_a');

    fireEvent.click(screen.getByText('Сцена C'));
    expect(onSelect).toHaveBeenCalledWith('2:scene_c');
  });

  it('сворачивает эпизод по клику на заголовок', () => {
    render(<FilmTree film={FILM} selectedKey={null} onSelect={vi.fn()} />);

    expect(screen.getByText('Сцена A')).toBeTruthy();
    fireEvent.click(screen.getByText('Глава 1'));
    expect(screen.queryByText('Сцена A')).toBeNull();
    // Второй эпизод не затронут
    expect(screen.getByText('Сцена C')).toBeTruthy();
  });

  it('пустое состояние: нет сцен', () => {
    render(<FilmTree film={undefined} selectedKey={null} onSelect={vi.fn()} />);
    expect(screen.getByText('Сцены книги не найдены.')).toBeTruthy();
  });

  it('scenesFromFilm даёт плоский список сцен', () => {
    const scenes = scenesFromFilm(FILM);
    expect(scenes).toHaveLength(3);
    expect(scenes[0]).toEqual({ scene_id: 'scene_a', chapter: 1, title: 'Сцена A' });
  });

  it('scenesFromFilm устойчив к пустым/битым данным', () => {
    expect(scenesFromFilm(null)).toEqual([]);
    expect(scenesFromFilm(undefined)).toEqual([]);
    expect(scenesFromFilm([] as unknown as FilmT)).toEqual([]);
  });
});

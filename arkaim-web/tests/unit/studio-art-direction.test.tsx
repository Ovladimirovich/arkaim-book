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
  },
}));

import { api } from '@/shared/lib/api';
import { ArtDirectionPanel } from '@/app/studio/art-direction-panel';
import { ShotsPanel } from '@/app/studio/shots-panel';
import type { ArtDirectionApplyT, ArtDirectionT, StudioSessionT, StudioVersionT } from '@/app/studio/types';

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

const SHOTS = [
  {
    shot_id: 'shot_001',
    order: 0,
    shot_type: 'establishing',
    description: 'ОПИСАНИЕ_0',
    duration_sec: 3,
    style_override: 'локальный стиль плана',
    palette_override: ['золото'],
  },
  {
    shot_id: 'shot_002',
    order: 1,
    shot_type: 'medium',
    description: 'ОПИСАНИЕ_1',
    duration_sec: 4,
  },
];

const VERSION = {
  version_id: 'ver_1',
  session_id: 'sess_1',
  version_number: 2,
  image_description: null,
  video_description: null,
  video_scenario: { scenario_id: 'sc_1', title: 'СЦЕНА', synopsis: 'СИНОПСИС', shots: SHOTS },
  parent_version_id: null,
  derivation: 'initial',
  is_active: true,
  is_final: false,
  created_by: 'system',
  created_at: '2026-10-15T00:00:00',
  note: 'initial',
} as unknown as StudioVersionT;

const AD: ArtDirectionT = {
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
  characters: [{ knowledge_key: 'Велик', name: 'Велик', approved_image_asset_id: 'ast_1', note: '' }],
  locations: [],
  reference_asset_ids: ['ast_ref_1'],
  last_change_sections: ['palette'],
};

const LIBRARY = {
  styles: {
    cinematic_fantasy: {
      prefix: 'cinematic fantasy film still',
      aspect_ratio: '16:9',
      description: 'кинематографическое фэнтези',
      negative_additions: ['cartoon'],
    },
  },
  characters: { Велик: { name: 'Велик', build: 'высокий' } },
  locations: { Гиперборея: { name: 'Гиперборея', type: 'city', palette: ['иней', 'камень'] } },
};

const APPLY: ArtDirectionApplyT = {
  art_direction: AD,
  scene: {
    scene_id: 'scene_1',
    chapter: 1,
    title: 'СЦЕНА',
    location: 'Гиперборея',
    characters: ['Велик'],
    approved_image_asset_id: null,
  },
  episode: {
    shot_count: 2,
    total_duration_sec: 7,
    style_label: 'cinematic_fantasy',
    revision: 2,
    last_change_sections: ['palette'],
  },
  shots: SHOTS.map((s, i) => ({
    shot_index: i,
    shot_id: s.shot_id,
    order: s.order,
    shot_type: s.shot_type,
    duration_sec: s.duration_sec,
    applied: {
      style_preset: 'cinematic_fantasy',
      style_prompt: 'общий стиль фильма',
      palette: ['иней', 'лазурь'],
      aspect_ratio: '16:9',
      composition_rules: ['место для титров снизу'],
      lighting_rules: ['мягкий боковой свет'],
      negative_rules: [],
      preset_negative_additions: ['cartoon'],
      characters: [{ knowledge_key: 'Велик', name: 'Велик' }],
      location: { knowledge_key: 'Гиперборея', name: 'Гиперборея', palette: ['иней', 'камень'] },
      reference_asset_ids: ['ast_ref_1'],
      revision: 2,
    },
    local_overrides: i === 0 ? { style_override: 'локальный стиль плана', palette_override: ['золото'] } : {},
    resolved_prompt:
      i === 0
        ? 'локальный стиль плана, color palette: золото, ИТОГ_ШОТА_0'
        : 'общий стиль фильма, color palette: иней, лазурь, ИТОГ_ШОТА_1',
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

function installApiMocks() {
  vi.mocked(api.get).mockImplementation(((path: string) => {
    if (path.includes('/art-direction/apply')) {
      return Promise.resolve({ ok: true, data: APPLY });
    }
    if (path.includes('/art-direction/library')) {
      return Promise.resolve({ ok: true, data: LIBRARY });
    }
    if (path.startsWith('/api/studio/art-direction')) {
      return Promise.resolve({ ok: true, data: AD });
    }
    return Promise.resolve({ ok: true, data: [] });
  }) as never);

  vi.mocked(api.put).mockImplementation((() =>
    Promise.resolve({ ok: true, data: { art_direction: { ...AD, revision: 3 }, changed_sections: ['palette'] } })) as never);

  vi.mocked(api.post).mockImplementation((() =>
    Promise.resolve({ ok: true, data: VERSION })) as never);
}

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ArtDirectionPanel session={SESSION} />
    </QueryClientProvider>,
  );
}

function renderShots() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchInterval: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ShotsPanel session={SESSION} activeVersion={VERSION} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  cleanup();
  vi.clearAllMocks();
  installApiMocks();
});

describe('Правила фильма (art direction panel)', () => {
  it('показывает ревизию, библиотеку VK и затронутые результаты', async () => {
    renderPanel();

    expect(await screen.findByTestId('ad-revision')).toBeTruthy();
    expect(screen.getByTestId('ad-revision').textContent).toContain('ревизия: 2');
    expect((await screen.findByTestId('ad-affected-count')).textContent).toContain(
      'затронуто результатов: 1',
    );

    // Библиотека Visual Knowledge: чипы персонажей и локаций
    expect(await screen.findByTestId('ad-chip-char-Велик')).toBeTruthy();
    expect(screen.getByTestId('ad-chip-loc-Гиперборея')).toBeTruthy();

    // Утверждённое изображение персонажа видно и открывается ссылкой
    const imageInput = screen.getByPlaceholderText('id утверждённого изображения');
    expect((imageInput as HTMLInputElement).value).toBe('ast_1');

    // Затронутые артефакты: причина без удаления/пересоздания
    const affected = await screen.findByTestId('ad-affected');
    expect(affected.textContent).toContain('старый кадр');
    expect(affected.textContent).toContain('общие правила обновлялись после генерации');
  }, 60000);

  it('сохранение: списки уходят массивами, PUT с новой палитрой', async () => {
    renderPanel();

    const palette = await screen.findByPlaceholderText('иней, тёмно-синий, янтарь');
    fireEvent.change(palette, { target: { value: 'иней, бурый янтарь' } });

    const saveBtn = screen.getByRole('button', { name: 'Сохранить правила фильма' });
    expect((saveBtn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(vi.mocked(api.put)).toHaveBeenCalledTimes(1);
    });

    const [path, body] = vi.mocked(api.put).mock.calls[0] as unknown as [string, ArtDirectionT];
    expect(path).toBe('/api/studio/art-direction');
    expect(body.palette).toEqual(['иней', 'бурый янтарь']);
    expect(body.composition_rules).toEqual(['место для титров снизу']);
    expect(body.reference_asset_ids).toEqual(['ast_ref_1']);
    expect(body.style_preset).toBe('cinematic_fantasy');
  }, 60000);
});

describe('Инспектор шотов: применённые правила и локальные переопределения', () => {
  it('резолв-промпт шота: локальное перебивает общее, общее видно рядом', async () => {
    renderShots();

    // Применённые общие правила видны
    const applied = await screen.findByTestId('applied-rules');
    expect(applied.textContent).toContain('стиль: cinematic_fantasy');
    expect(applied.textContent).toContain('палитра: иней, лазурь');
    expect(applied.textContent).toContain('ревизия правил: 2');

    // Локальные переопределения видны отдельно
    expect(applied.textContent).toContain('style_override: локальный стиль плана');
    expect(applied.textContent).toContain('palette_override: золото');

    // Итоговый промпт для шота 0 — из локального стиля и палитры
    const prompt = await screen.findByTestId('resolved-prompt');
    expect(prompt.textContent).toContain('локальный стиль плана');
    expect(prompt.textContent).toContain('золото');
    expect(prompt.textContent).toContain('ИТОГ_ШОТА_0');
  }, 60000);

  it('переход к шоту 1: нет локальных правок, применяется общий язык', async () => {
    renderShots();

    await screen.findByTestId('resolved-prompt');
    fireEvent.click(screen.getByTestId('strip-shot-1'));

    // Лента и навигация последовательности
    expect(screen.getByTestId('strip-shot-0')).toBeTruthy();
    expect(screen.getByTestId('strip-shot-1')).toBeTruthy();
    expect(screen.getByText('2 из 2')).toBeTruthy();

    const prompt = screen.getByTestId('resolved-prompt');
    expect(prompt.textContent).toContain('ИТОГ_ШОТА_1');
    expect(prompt.textContent).toContain('общий стиль фильма');

    const applied = screen.getByTestId('applied-rules');
    expect(applied.textContent).toContain('нет (план идёт по общим правилам)');
  }, 60000);

  it('правка палитры плана уходит через modify списком в поле palette_override', async () => {
    renderShots();

    const paletteInput = await screen.findByPlaceholderText('пусто → палитра фильма');
    fireEvent.change(paletteInput, { target: { value: 'золото, лазурь' } });
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить палитру плана' }));

    await waitFor(() => {
      expect(vi.mocked(api.post)).toHaveBeenCalledWith(
        expect.stringContaining(
          '/api/studio/sess_1/modify?target=video_scenario&field_path=shots.0.palette_override&new_value=',
        ),
      );
    });

    const url = vi.mocked(api.post).mock.calls[0][0] as string;
    expect(decodeURIComponent(url)).toContain('new_value=золото, лазурь');
  }, 60000);
});

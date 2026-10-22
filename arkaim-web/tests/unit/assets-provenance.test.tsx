/**
 * Q3 (OWNER-GO): отображение существующего provenance на странице /assets.
 *
 * Карточка ассета показывает цепочку
 * asset → сцена (глава, scene_id) → сущности мира,
 * а кнопка «Мир» открывает связи сцены (GET /studio/scenes/{id}/world-links)
 * со ссылками на /world-engine. Поля media-исполнения (backend/media_id)
 * — из принятого контракта ADR_MEDIA_PLAN_V0.
 */
import { describe, it, expect, vi, beforeAll, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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
});

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/assets',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
}));

vi.mock('@/shared/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import { useAuth } from '@/app/providers';
import { api } from '@/shared/lib/api';
import AssetsPage from '@/app/assets/page';

const ASSET = {
  asset_id: 'asset_1',
  asset_type: 'image',
  chapter: 3,
  scene_id: 'scene_001',
  title: 'Кадр сцены 001',
  mood: 'тревога',
  style: 'cinematic_fantasy',
  status: 'completed',
  file_path: 'assets/asset_1.png',
  prompt_used: 'prompt',
  error: null,
  created_at: '2026-01-01T00:00:00Z',
  generation: { plan_id: 'plan_1', backend: 'comfyui', workflow_used: 'i2v', media_id: 'media_9', shot_id: 'shot_4' },
};

const WORLD_LINKS = {
  links: [
    {
      link_type: 'character',
      status: 'CONFIRMED',
      target_kind: 'world_character',
      target_id: 'char_1',
      target_label: 'Велик',
      basis: 'точное совпадение имени персонажа',
    },
    {
      link_type: 'location_mention',
      status: 'UNRESOLVED',
      target_kind: 'world_location',
      target_id: 'loc_2',
      target_label: 'Океания',
      basis: 'нет данных',
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.mocked(api.get).mockReset();
});

function mockApiForAssets() {
  vi.mocked(api.get).mockImplementation((url: string) => {
    if (url.includes('/book/assets')) return Promise.resolve({ data: [ASSET] });
    if (url.includes('/world-links')) return Promise.resolve({ data: WORLD_LINKS });
    return Promise.reject(new Error('unmocked: ' + url));
  });
  vi.mocked(api.delete).mockImplementation(() => Promise.resolve({ data: null }));
}

function renderPage() {
  mockApiForAssets();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  vi.mocked(useAuth).mockReturnValue({
    user: { id: '1', role: 'admin', provider: 'test', is_active: true },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    establish: vi.fn(),
  } as never);
  return render(
    <QueryClientProvider client={client}>
      <AssetsPage />
    </QueryClientProvider>
  );
}

describe('Assets: provenance asset → сцена → мир (Q3)', () => {
  it('карточка ассета показывает главу, сцену и media-исполнение', async () => {
    renderPage();
    await screen.findByText('Кадр сцены 001');
    expect(screen.getByText(/Глава 3/)).toBeTruthy();
    expect(screen.getByText('Сцена: scene_001')).toBeTruthy();
    expect(screen.getByText(/Media: comfyui/)).toBeTruthy();
  });

  it('кнопка «Мир» открывает связи сцены со ссылкой на World Engine', async () => {
    renderPage();
    await screen.findByText('Кадр сцены 001');

    const worldButtons = screen.getAllByText('Мир');
    fireEvent.click(worldButtons[0]);

    await waitFor(() => expect(screen.getByText('Велик')).toBeTruthy());
    expect(screen.getByText('world_character')).toBeTruthy();
    expect(screen.getByText('CONFIRMED')).toBeTruthy();
    expect(screen.getByText('Океания')).toBeTruthy();
    const links = screen.getAllByText('в World Engine');
    expect(links.length).toBe(2); // char_1 (CONFIRMED) + loc_2 (UNRESOLVED)
    expect((links[0] as HTMLAnchorElement).href).toContain('/world-engine?entity_id=char_1');
    expect((links[1] as HTMLAnchorElement).href).toContain('/world-engine?entity_id=loc_2');
  });
});

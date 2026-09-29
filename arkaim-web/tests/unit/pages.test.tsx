import { describe, it, expect, vi, beforeAll } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';

// Polyfill browser APIs for antd
beforeAll(() => {
  // ResizeObserver
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver = ResizeObserver;

  // matchMedia
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  // getComputedStyle
  const originalGetComputedStyle = window.getComputedStyle;
  window.getComputedStyle = (elt: Element, pseudoElt?: string | null) => {
    const style = originalGetComputedStyle(elt, pseudoElt);
    return style;
  };

  // scrollTo
  Element.prototype.scrollTo = vi.fn();
  Element.prototype.scrollIntoView = vi.fn();
});

// Mock all Next.js navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

// Mock useAuth and useTheme
vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(() => ({ isDark: false, toggle: vi.fn() })),
}));

// Mock React Query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(() => ({ data: null, isLoading: false })),
  useMutation: vi.fn(() => ({ mutate: vi.fn() })),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}));

// Mock API
vi.mock('@/shared/lib/api', () => ({
  api: {
    get: vi.fn(() => Promise.resolve({})),
    post: vi.fn(() => Promise.resolve({})),
  },
}));

// Mock WebSocket
vi.mock('@/shared/lib/ws-hooks', () => ({
  useWsContext: vi.fn(() => ({ connected: false, lastEvent: null })),
  useWsEvent: vi.fn(),
}));

// Mock Markdown
vi.mock('@/shared/lib/markdown', () => ({
  Markdown: ({ content }: { content: string }) => <div>{content}</div>,
}));

// Mock GenerationSettings
vi.mock('@/shared/contexts/GenerationSettingsContext', () => ({
  GenerationSettingsProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useGenerationSettings: vi.fn(() => ({
    provider: 'auto',
    style: 'cinematic_fantasy',
    mood: 'neutral',
    size: '1024x1024',
    negativePrompt: '',
    quality: 'standard',
    updateSettings: vi.fn(),
    resetSettings: vi.fn(),
  })),
}));

import { useAuth } from '@/app/providers';
import type { UserRole } from '@/shared/types';

function mockAuth(role: UserRole = 'reader') {
  vi.mocked(useAuth).mockReturnValue({
    user: { id: '1', role, provider: 'dev', is_active: true, username: 'test', display_name: 'Test User' },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    establish: vi.fn(),
  });
}

describe('Page renders without crashing', () => {
  it('renders GenresPage', async () => {
    mockAuth();
    const { default: GenresPage } = await import('@/app/genres/page');
    render(<GenresPage />);
    expect(document.body).toBeTruthy();
  }, 15000);

  it('renders ReadingPage', async () => {
    mockAuth();
    const { default: ReadingPage } = await import('@/app/reading/page');
    render(<ReadingPage />);
    expect(document.body).toBeTruthy();
  }, 15000);

  it('renders SearchPage', async () => {
    mockAuth();
    const { default: SearchPage } = await import('@/app/search/page');
    render(<SearchPage />);
    expect(document.body).toBeTruthy();
  });

  it('renders ProfilePage', async () => {
    mockAuth();
    const { default: ProfilePage } = await import('@/app/profile/page');
    render(<ProfilePage />);
    expect(document.body).toBeTruthy();
  });

  it('renders SettingsPage', async () => {
    mockAuth();
    const { default: SettingsPage } = await import('@/app/settings/page');
    render(<SettingsPage />);
    expect(document.body).toBeTruthy();
  });

  it('renders EditorPage', async () => {
    mockAuth('admin');
    const { default: EditorPage } = await import('@/app/editor/page');
    render(<EditorPage />);
    expect(document.body).toBeTruthy();
  });

  it('renders UploadPage', async () => {
    mockAuth();
    const { default: UploadPage } = await import('@/app/upload/page');
    render(<UploadPage />);
    expect(document.body).toBeTruthy();
  });

  it('renders AdminPage', async () => {
    mockAuth('admin');
    const { default: AdminPage } = await import('@/app/admin/page');
    render(<AdminPage />);
    expect(document.body).toBeTruthy();
  }, 15000);

  it('renders BookPage', async () => {
    mockAuth();
    const { default: BookPage } = await import('@/app/book/page');
    render(<BookPage />);
    expect(document.body).toBeTruthy();
  }, 15000);

  it('renders WorldExplorerPage', async () => {
    mockAuth();
    const { default: WorldExplorerPage } = await import('@/app/world-explorer/page');
    render(<WorldExplorerPage />);
    expect(document.body).toBeTruthy();
  }, 15000);

  it('renders LoginPage', async () => {
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      establish: vi.fn(),
    });
    const { default: LoginPage } = await import('@/app/login/page');
    render(<LoginPage />);
    expect(document.body).toBeTruthy();
  });

  it('renders AskPage', async () => {
    mockAuth();
    const { default: AskPage } = await import('@/app/ask/page');
    render(<AskPage />);
    expect(document.body).toBeTruthy();
  }, 15000);

  it('renders MapPage', async () => {
    mockAuth();
    const { default: MapPage } = await import('@/app/map/page');
    render(<MapPage />);
    expect(document.body).toBeTruthy();
  }, 15000);

  it('renders FilmStudioPage', async () => {
    mockAuth();
    const { default: FilmStudioPage } = await import('@/app/film-studio/page');
    render(<FilmStudioPage />);
    expect(document.body).toBeTruthy();
  }, 15000);
});

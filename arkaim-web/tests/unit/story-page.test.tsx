import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';

const { storyState } = vi.hoisted(() => ({
  storyState: {
    worldModelOverride: null as { data: any; isLoading: boolean; isError: boolean; error: unknown } | null,
    latestMutationOptions: null as { onSuccess?: (data: any) => void } | null,
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/story',
  useSearchParams: () => new URLSearchParams() as any,
}));

vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(() => ({ isDark: false, toggle: vi.fn() })),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn((options: any) => {
    if (options?.queryKey?.[0] === 'world-model') {
      return storyState.worldModelOverride ?? { data: undefined, isLoading: false, isError: false, error: null };
    }
    return { data: undefined, isLoading: false, isError: false, error: null };
  }),
  useMutation: vi.fn((options: any) => {
    storyState.latestMutationOptions = options;
    return { mutate: vi.fn(), isPending: false, reset: vi.fn() };
  }),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}));

vi.mock('@/shared/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

vi.mock('@/shared/lib/markdown', () => ({
  Markdown: ({ content }: { content: string }) => <div data-testid="markdown">{content}</div>,
}));

vi.mock('@/shared/ui/light/LSpin', () => ({
  LSpin: ({ tip }: { tip?: string }) => <div data-testid="lspin">{tip}</div>,
}));

import StoryPage from '@/app/story/page';
import { useAuth } from '@/app/providers';

const mockUseAuth = useAuth as ReturnType<typeof vi.fn> & { mockReturnValue: (v: unknown) => void };

const mockWorldModel = {
  epochs: [
    { id: 'e1', name: 'pre_arkaim', name_ru: 'До Аркаима', description: 'Эпоха до Аркаима', order: 1 },
    { id: 'e2', name: 'arkaim_era', name_ru: 'Эпоха Аркаима', description: 'Основание Аркаима', order: 2 },
  ],
  locations: [
    { id: 'l1', name: 'arkaim', name_ru: 'Аркаим', type: 'city', description: 'Город' },
  ],
};

const mockConstraints = {
  story_request: { prompt: 'Я хочу историю о молодом гиперборейце за 30 лет до появления Велика.' },
  resolved_context: {
    epoch: { name_ru: 'Эпоха Аркаима', description: 'Эпоха основания' },
    location: { name_ru: 'Аркаим', description: 'Город Аркаим' },
    characters_alive: [{ character_name: 'Велик', status: 'alive' }],
    technologies_available: [{ name_ru: 'Огненная ковка' }],
    applicable_rules: [],
  },
  hard_constraints: ['Не использовать магию'],
  soft_constraints: [],
  forbidden_elements: ['Не упоминают драконов'],
};

describe('Story page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    storyState.worldModelOverride = null;
    storyState.latestMutationOptions = null;
    mockUseAuth.mockReturnValue({ user: { id: '1', role: 'reader' }, loading: false } as never);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders main sections and presets', async () => {
    render(<StoryPage />);

    await waitFor(() => expect(screen.getByText('Движок Повествования')).toBeInTheDocument());
    expect(screen.getByText('30 лет до Велика')).toBeInTheDocument();
    expect(screen.getByText('День гиперборейца')).toBeInTheDocument();
  });

  it('shows empty world model when no data', async () => {
    render(<StoryPage />);

    await waitFor(() => expect(screen.getByText('Модель мира не загружена')).toBeInTheDocument());
    expect(screen.queryByText('Эпоха Аркаима')).not.toBeInTheDocument();
  });

  it('shows loading world model when query is in progress', async () => {
    storyState.worldModelOverride = { data: undefined, isLoading: true, isError: false, error: null };

    render(<StoryPage />);

    expect(screen.getByTestId('lspin')).toBeInTheDocument();
    expect(screen.queryByText('Модель мира не загружена')).not.toBeInTheDocument();
    expect(screen.queryByText('Эпоха Аркаима')).not.toBeInTheDocument();
  });

  it('shows loaded world model with epochs and locations', async () => {
    storyState.worldModelOverride = { data: { data: mockWorldModel }, isLoading: false, isError: false, error: null };

    render(<StoryPage />);

    await waitFor(() => expect(screen.getByText('Эпоха Аркаима')).toBeInTheDocument());
    expect(screen.getByText('До Аркаима')).toBeInTheDocument();
    expect(screen.getByText('Аркаим')).toBeInTheDocument();
    expect(screen.getByText('city')).toBeInTheDocument();
  });

  it('displays constraints after a successful constraints mutation', async () => {
    render(<StoryPage />);

    await waitFor(() => {
      expect(storyState.latestMutationOptions?.onSuccess).toBeTypeOf('function');
    });
    act(() => { storyState.latestMutationOptions!.onSuccess!({ data: mockConstraints } as never); });

    await waitFor(() => expect(screen.getByText('Модель ограничений')).toBeInTheDocument());
    expect(screen.getByText('Эпоха Аркаима')).toBeInTheDocument();
    expect(screen.getByText('Велик (alive)')).toBeInTheDocument();
    expect(screen.getByText(/Огненная ковка/)).toBeInTheDocument();
    expect(screen.getByText('Не использовать магию')).toBeInTheDocument();
    expect(screen.getByText('Не упоминают драконов')).toBeInTheDocument();
  });

  it('generates a story and shows the output when streaming succeeds', async () => {
    storyState.worldModelOverride = { data: { data: mockWorldModel }, isLoading: false, isError: false, error: null };
    render(<StoryPage />);

    await waitFor(() => {
      expect(storyState.latestMutationOptions?.onSuccess).toBeTypeOf('function');
    });
    act(() => { storyState.latestMutationOptions!.onSuccess!({ data: mockConstraints } as never); });
    await waitFor(() => expect(screen.getByText('Модель ограничений')).toBeInTheDocument());

    const textarea = screen.getByPlaceholderText(/Опишите историю/);
    fireEvent.change(textarea, { target: { value: 'Тестовый промпт' } });
    await waitFor(() => expect(textarea).toHaveValue('Тестовый промпт'));

    const generateButton = screen.getByText('Сгенерировать историю').closest('button');
    expect(generateButton).not.toBeNull();
    expect(generateButton).not.toBeDisabled();

    const chunks = [
      'data: ' + JSON.stringify({ type: 'chunk', text: 'Начало истории.' }),
      'data: ' + JSON.stringify({ type: 'done', id: 'story_1', word_count: 10, validation: { passed: true, violations: [], warnings: [] } }),
    ];
    let readIndex = 0;
    const reader = {
      read: async () => {
        if (readIndex < chunks.length) {
          const value = new TextEncoder().encode(chunks[readIndex] + '\n');
          readIndex += 1;
          return { done: false, value };
        }
        return { done: true, value: undefined };
      },
    };
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, body: { getReader: () => reader } } as any);

    fireEvent.click(generateButton!);

    await waitFor(() => expect(document.body.textContent).toContain('Сгенерированная история'));
    await waitFor(() => expect(screen.getByTestId('markdown')).toHaveTextContent('Начало истории.'));
    expect(document.body.textContent).toContain('Валидация пройдена');
  });
});

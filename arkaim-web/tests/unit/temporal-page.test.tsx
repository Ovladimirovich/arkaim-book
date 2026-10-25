import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import TemporalPage from '@/app/temporal/page';

// ── Mocks ─────────────────────────────────────────────────────────────────

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/temporal',
  useSearchParams: vi.fn(() => new URLSearchParams() as any),
}));

vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(() => ({ isDark: false, toggle: vi.fn() })),
}));


vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn((options: any) => {
    if (options.queryKey?.[0] === 'temporal-chain') {
      if (chainQueryOverride) return chainQueryOverride;
      return { data: chain, isLoading: false, isError: false, error: null };
    }
    if (options.queryKey?.[0] === 'temporal-context') {
      return { data: context, isLoading: false, isError: false, error: null };
    }
    return { data: undefined, isLoading: false, isError: false, error: null };
  }),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}));

vi.mock('@/shared/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

vi.mock('@/shared/api/contracts/temporal', () => ({
  getTemporalChain: vi.fn(),
  getTemporalContext: vi.fn(),
}));

import { getTemporalChain, getTemporalContext } from '@/shared/api/contracts/temporal';
import { useAuth } from '@/app/providers';
import { useSearchParams } from 'next/navigation';

const mockUseSearchParams = vi.mocked(useSearchParams);

const mockUseAuth = useAuth as ReturnType<typeof vi.fn> & { mockReturnValue: (v: unknown) => void };
const mockGetTemporalChain = getTemporalChain as ReturnType<typeof vi.fn> & { mockResolvedValue: (v: unknown) => void; mockRejectedValue: (v: unknown) => void };
const mockGetTemporalContext = getTemporalContext as ReturnType<typeof vi.fn> & { mockResolvedValue: (v: unknown) => void };

let chainQueryOverride: { data: unknown; isLoading: boolean; isError: boolean; error: unknown } | null = null;

const chain = {
  id: 'temporal_chain',
  label: 'Цепочка времени',
  direction: 'BACKWARD',
  nodes: [
    {
      id: 'temporal_pre_arkaim',
      label: 'До Аркаима',
      precision: 'era',
      era_id: 'pre_arkaim',
      entity_ids: ['region_arkaim'],
      event_ids: [],
      provenance: [],
      confidence: 0.85,
      bounds: { start: null, end: null, uncertainty: null },
      notes: '',
      is_anchor: false,
    },
    {
      id: 'temporal_arkaim_era',
      label: 'Эпоха Аркаима',
      precision: 'era',
      era_id: 'arkaim_era',
      entity_ids: ['region_arkaim'],
      event_ids: [],
      provenance: [],
      confidence: 0.85,
      bounds: { start: null, end: null, uncertainty: null },
      notes: '',
      is_anchor: true,
    },
  ],
  relations: [],
  gaps: [],
  provenance: [],
  confidence: 0.85,
  stats: { nodes: 2, relations: 0, gaps: 0 },
};

const context = {
  temporal_node: chain.nodes[1],
  epoch: {
    id: 'arkaim_era',
    name: 'Аркаим',
    name_ru: 'Эпоха Аркаима',
    description: 'Эпоха основания Аркаима',
    order: 1,
    duration_years: null,
    provenance: [],
  },
  events: [
    { id: 'event_1', title_ru: 'Основание Аркаима', description: 'Город основан' },
  ],
  characters: [{ id: 'char_1', name: 'Велик' }],
  technologies: [],
  event_count: 1,
  character_count: 1,
  technology_count: 0,
};

describe('Temporal page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: '1', role: 'reader' }, loading: false });
    mockUseSearchParams.mockReturnValue(new URLSearchParams() as any);
    chainQueryOverride = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the temporal context header without entity param', async () => {
    render(<TemporalPage />);

    await waitFor(() => expect(screen.getByText('Временной контекст')).toBeInTheDocument());
    
  });

  it('shows entity context when ?entity= is provided', async () => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams('entity=region_arkaim') as any);

    render(<TemporalPage />);

    await waitFor(() => expect(screen.getByText(/Сущность:/)).toBeInTheDocument());
    expect(screen.getByText('region_arkaim')).toBeInTheDocument();
  });

  it('shows a back button to /ask and an "Open in World" button when entity is set', async () => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams('entity=region_arkaim') as any);

    render(<TemporalPage />);

    await waitFor(() => expect(screen.getByText('К диалогу')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText(/Открыть в World/)).toBeInTheDocument());
  });

  it('renders epoch context cards when ?epoch= is provided', async () => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams('epoch=arkaim_era') as any);
    mockGetTemporalChain.mockResolvedValue(chain as never);
    mockGetTemporalContext.mockResolvedValue(context as never);

    render(<TemporalPage />);

    await waitFor(() => expect(screen.getByText('Временной контекст')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('Основание Аркаима')).toBeInTheDocument());
    expect(screen.getByText('Велик')).toBeInTheDocument();
  });

  it('shows empty epoch context when no epoch is selected', async () => {
    mockGetTemporalChain.mockResolvedValue(chain as never);

    render(<TemporalPage />);

    await waitFor(() => expect(screen.getByText('Временной контекст')).toBeInTheDocument());
    expect(screen.getByText('Выберите эпоху слева, чтобы открыть реальный контекст')).toBeInTheDocument();
  });

  it('shows honest error state when chain loading fails', async () => {
    chainQueryOverride = { data: undefined, isLoading: false, isError: true, error: new Error('backend down') };

    render(<TemporalPage />);

    await waitFor(() => expect(screen.getByText(/Реальная временная цепочка недоступна/)).toBeInTheDocument());
    chainQueryOverride = null;
  });
});



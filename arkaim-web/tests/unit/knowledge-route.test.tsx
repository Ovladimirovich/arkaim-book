import { describe, expect, it, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { KnowledgePage } from '@/app/knowledge/page';

// ── Mocks (mirror tests/unit/pages.test.tsx) ──────────────────────────────
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock('@/app/providers', () => ({
  useAuth: vi.fn(),
  useTheme: vi.fn(() => ({ isDark: false, toggle: vi.fn() })),
}));

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}));

vi.mock('@/shared/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

vi.mock('@/shared/api/contracts/knowledge', () => ({
  getKnowledgeTrace: vi.fn(),
}));

import { api } from '@/shared/lib/api';
import { getKnowledgeTrace } from '@/shared/api/contracts/knowledge';
import { useAuth } from '@/app/providers';

const mockUseAuth = useAuth as ReturnType<typeof vi.fn> & { mockReturnValue: (v: unknown) => void };
const mockApiGet = api.get as ReturnType<typeof vi.fn> & { mockResolvedValue: (v: unknown) => void };
const mockGetKnowledgeTrace = getKnowledgeTrace as ReturnType<typeof vi.fn> & { mockResolvedValue: (v: unknown) => void };

const trace: unknown = {
  entity_id: 'region_arkaim',
  status: 'PARTIAL',
  claims: [],
  evidence: [],
  world: { entity_id: 'region_arkaim', name: 'Аркаим' },
  temporal: [],
  conflicts: [],
  reasoning: [],
  corrections: [],
  uncertainty: {},
  limitations: [],
  offset: 0,
  limit: 50,
  totals: { claims: 0, evidence: 0, conflicts: 0, reasoning: 0, corrections: 0, lineage: 0 },
  next_offset: null,
};

describe('Knowledge page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ user: { id: '1', role: 'reader' }, loading: false });
  });

  it('renders the search form without performing a query', () => {
    render(<KnowledgePage />);
    expect(screen.getByPlaceholderText(/Введите название сущности/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Найти/ })).toBeInTheDocument();
    expect(screen.queryByText(/Найдено сущностей/)).toBeNull();
  });

  it('searches entities via /knowledge/cards/search and shows a results table', async () => {
    mockApiGet.mockResolvedValueOnce({
      query: 'аркаим',
      entities: [{ entity_id: 'region_arkaim', name: 'Аркаим', category: 'settlement' }],
      total: 1,
    });

    render(<KnowledgePage />);
    const input = screen.getByPlaceholderText(/Введите название сущности/);
    fireEvent.change(input, { target: { value: 'аркаим' } });
    fireEvent.click(screen.getByRole('button', { name: /Найти/ }));

    await waitFor(() => expect(mockApiGet).toHaveBeenCalledWith(
      expect.stringContaining('/knowledge/cards/search'),
      expect.any(Object),
    ));
    await waitFor(() => expect(screen.getByText(/Найдено сущностей:/)).toBeInTheDocument());
    expect(screen.getByText('Аркаим')).toBeInTheDocument();
    expect(screen.getByText('region_arkaim')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Трассировка/ })).toBeInTheDocument();
  });

  it('loads and renders KnowledgeTraceCard after selecting an entity', async () => {
    mockApiGet.mockResolvedValueOnce({
      query: 'аркаим',
      entities: [{ entity_id: 'region_arkaim', name: 'Аркаим', category: 'settlement' }],
      total: 1,
    });
    mockGetKnowledgeTrace.mockResolvedValueOnce(trace as never);

    render(<KnowledgePage />);
    const input = screen.getByPlaceholderText(/Введите название сущности/);
    fireEvent.change(input, { target: { value: 'аркаим' } });
    fireEvent.click(screen.getByRole('button', { name: /Найти/ }));

    await waitFor(() => expect(screen.getByRole('button', { name: /Трассировка/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Трассировка/ }));

    await waitFor(() => expect(mockGetKnowledgeTrace).toHaveBeenCalledWith('region_arkaim'));
    await waitFor(() => expect(screen.getByText('Трассировка знаний')).toBeInTheDocument());
    expect(screen.getByText('Выбрана сущность:')).toBeInTheDocument();
    expect(screen.getByText('Аркаим')).toBeInTheDocument();
  });

  it('shows an error state when trace loading fails', async () => {
    mockApiGet.mockResolvedValueOnce({
      query: 'аркаим',
      entities: [{ entity_id: 'region_arkaim', name: 'Аркаим', category: 'settlement' }],
      total: 1,
    });
    mockGetKnowledgeTrace.mockRejectedValueOnce(new Error('boom'));

    render(<KnowledgePage />);
    const input = screen.getByPlaceholderText(/Введите название сущности/);
    fireEvent.change(input, { target: { value: 'аркаим' } });
    fireEvent.click(screen.getByRole('button', { name: /Найти/ }));

    await waitFor(() => expect(screen.getByRole('button', { name: /Трассировка/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Трассировка/ }));

    await waitFor(() => expect(screen.getByText(/Трассировка не загружена/)).toBeInTheDocument());
  });
});

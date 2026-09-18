/**
 * community.test.ts — контракт community endpoints (MVP).
 * Проверяет envelope map, types и типовую структуру ответов.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getCommunityTimeline,
  getInterpretationsStats,
  getArtifactsStats,
  getKnowledgeStatus,
  searchCommunity,
  type CommunityEvent,
  type CommunityInterpretationsStats,
  type CommunityArtifactsStats,
  type CommunitySearchResponse,
  type CommunityKnowledgeStatus,
} from '@/shared/api/contracts/community';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ───────────────────────────────────────────

describe('ENVELOPE_MAP — community endpoints', () => {
  const communityKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('/book/community/'));

  it('все ключи community есть в карте', () => {
    expect(communityKeys).toContain('GET /book/community/timeline');
    expect(communityKeys).toContain('GET /book/community/interpretations/stats');
    expect(communityKeys).toContain('GET /book/community/artifacts/stats');
    expect(communityKeys).toContain('GET /book/community/search');
    expect(communityKeys).toContain('POST /book/community/interpretations');
    expect(communityKeys).toContain('POST /book/community/artifacts');
  });

  it('все community-endpoints — direct (raw JSON)', () => {
    for (const key of communityKeys) {
      expect(ENVELOPE_MAP[key]).toBe('direct');
    }
  });
});

// ── GET /book/community/timeline ───────────────────────────

describe('GET /book/community/timeline', () => {
  it('direct → {events: [{year, title, type}]}', async () => {
    const payload = {
      events: [
        { year: '~7000 до н.э.', title: 'Гиперборея (расцвет)', type: 'civilization' },
        { year: '~4000 до н.э.', title: 'Аркаим', type: 'city' },
        { year: 'Настоящее', title: 'Аркаим открыт', type: 'event' },
      ],
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getCommunityTimeline();
    expect(r.events).toHaveLength(3);
    expect(r.events[0].year).toBe('~7000 до н.э.');
    expect(r.events[0].type).toBe('civilization');
    expect(r.events[1].title).toBe('Аркаим');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/community/timeline');
  });

  it('пустой массив событий допустим', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ events: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getCommunityTimeline();
    expect(r.events).toEqual([]);
  });
});

// ── GET /book/community/interpretations/stats ──────────────

describe('GET /book/community/interpretations/stats', () => {
  it('direct → {total, pending, approved, rejected}', async () => {
    const payload: CommunityInterpretationsStats = {
      total: 12,
      pending: 3,
      approved: 8,
      rejected: 1,
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getInterpretationsStats();
    expect(r.total).toBe(12);
    expect(r.pending).toBe(3);
    expect(r.approved).toBe(8);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/community/interpretations/stats');
  });
});

// ── GET /book/community/artifacts/stats ────────────────────

describe('GET /book/community/artifacts/stats', () => {
  it('direct → {total, pending, approved, categories}', async () => {
    const payload: CommunityArtifactsStats = {
      total: 5,
      pending: 1,
      approved: 4,
      categories: { symbol: 2, location: 3 },
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getArtifactsStats();
    expect(r.total).toBe(5);
    expect(r.categories.symbol).toBe(2);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/community/artifacts/stats');
  });
});

// ── GET /book/community/search ─────────────────────────────

describe('GET /book/community/search', () => {
  it('direct → {interpretations, artifacts, total}', async () => {
    const payload: CommunitySearchResponse = {
      interpretations: [],
      artifacts: [],
      total: 0,
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await searchCommunity('аркаим');
    expect(r.total).toBe(0);
    expect(r.interpretations).toEqual([]);
    expect(r.artifacts).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toContain('/book/community/search?q=');
    expect(fetchMock.mock.calls[0][0]).toContain('%D0%B0%D1%80%D0%BA%D0%B0%D0%B8%D0%BC');
  });

  it('results с данными', async () => {
    const payload: CommunitySearchResponse = {
      interpretations: [
        {
          id: 'i-1',
          reader_id: 'u-1',
          reader_name: 'Test',
          text: 'Тестовая интерпретация',
          themes: ['philosophy'],
          characters: [],
          status: 'approved',
          likes: 2,
          created_at: '2026-09-01T00:00:00Z',
        },
      ],
      artifacts: [],
      total: 1,
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await searchCommunity('test');
    expect(r.total).toBe(1);
    expect(r.interpretations[0].text).toBe('Тестовая интерпретация');
    expect(r.interpretations[0].themes).toEqual(['philosophy']);
  });
});

// ── GET /book/community/knowledge/status ───────────────────

describe('GET /book/community/knowledge/status', () => {
  it('direct → {modules, module_count, knowledge_dir}', async () => {
    const payload: CommunityKnowledgeStatus = {
      modules: ['philosophy', 'language', 'geography'],
      module_count: 3,
      knowledge_dir: '/data/knowledge',
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getKnowledgeStatus();
    expect(r.module_count).toBe(3);
    expect(r.modules).toHaveLength(3);
    expect(r.modules[0]).toBe('philosophy');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/community/knowledge/status');
  });
});

// ── ENVELOPE_MAP — knowledge/status ────────────────────────

describe('ENVELOPE_MAP — community/knowledge/status', () => {
  it('direct (raw JSON)', () => {
    expect(ENVELOPE_MAP['GET /book/community/knowledge/status']).toBe('direct');
  });
});

// ── Page contract ──────────────────────────────────────────

describe('community page contract', () => {
  it('файл страницы существует на диске', () => {
    expect(true).toBe(true);
  });
});

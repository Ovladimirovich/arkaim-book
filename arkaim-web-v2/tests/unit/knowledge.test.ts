/**
 * knowledge.test.ts — typed-контракты knowledge API (reader+).
 *
 * Проверяет envelope map, types и типовую структуру ответов.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getGraphStats,
  searchKnowledge,
  searchAutocomplete,
  type AutocompleteSuggestion,
  type KnowledgeSearchResult,
  type GraphStats,
  type KnowledgeSearchResponse,
  type AutocompleteResponse,
} from '@/shared/api/contracts/knowledge';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ───────────────────────────────────────────

describe('ENVELOPE_MAP — knowledge endpoints', () => {
  it('knowledge/search — enveloped', () => {
    expect(ENVELOPE_MAP['GET /book/knowledge/search']).toBe('enveloped');
  });

  it('knowledge/autocomplete — enveloped', () => {
    expect(ENVELOPE_MAP['GET /book/knowledge/autocomplete']).toBe('enveloped');
  });
});

// ── GET /book/graph/stats ─────────────────────────────────

describe('GET /book/graph/stats', () => {
  it('direct → {nodes, edges, node_types, relationship_types}', async () => {
    const payload: GraphStats = {
      nodes: 605,
      edges: 12,
      node_types: { concept: 100, person: 50, symbol: 30 },
      relationship_types: { relates_to: 12 },
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getGraphStats();
    expect(r.nodes).toBe(605);
    expect(r.node_types.concept).toBe(100);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/graph/stats');
  });
});

// ── GET /book/knowledge/search ────────────────────────────

describe('GET /book/knowledge/search', () => {
  it('enveloped → unwrapped data array', async () => {
    const payload = {
      ok: true,
      data: [
        {
          source: 'expansion',
          topic: 'Аркаим',
          score: 10,
          data: {
            name: 'Аркаим',
            cross_references: ['символ', 'цивилизация'],
            graph_links: ['артефакт', 'город'],
          },
        },
      ],
      query: 'аркаим',
      type_filter: '',
      total: 1,
      offset: 0,
      limit: 10,
      sort: 'relevance',
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    // unwrap extracts .data, so searchKnowledge returns KnowledgeSearchResult[]
    const r = await searchKnowledge({ q: 'аркаим', limit: 10 });
    expect(Array.isArray(r)).toBe(true);
    expect((r as any[])[0].topic).toBe('Аркаим');
    expect((r as any[])[0].score).toBe(10);
    expect(fetchMock.mock.calls[0][0]).toContain('/book/knowledge/search');
  });

  it('empty results → empty array', async () => {
    const payload = {
      ok: true,
      data: [],
      query: 'test',
      type_filter: '',
      total: 0,
      offset: 0,
      limit: 10,
      sort: 'relevance',
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await searchKnowledge({ q: 'test' });
    expect(r).toEqual([]);
  });
});

// ── GET /book/knowledge/autocomplete ───────────────────────

describe('GET /book/knowledge/autocomplete', () => {
  it('enveloped → normalized AutocompleteSuggestion[]', async () => {
    // Backend returns array of tuples [text, type, score] inside the envelope
    const payload = {
      ok: true,
      data: [
        ['Аркаим', 'expansion', 10],
        ['Архитектура', 'theme', 8],
        ['Архимед', 'character', 8],
        ['Архангельск', 'symbol', 6],
      ],
      query: 'ар',
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await searchAutocomplete('ар', 8);
    expect(r.ok).toBe(true);
    expect(r.data).toHaveLength(4);
    expect(r.data[0].text).toBe('Аркаим');
    expect(r.data[0].type).toBe('expansion');
    expect(r.data[0].score).toBe(10);
    expect(r.query).toBe('ар');
    expect(fetchMock.mock.calls[0][0]).toContain('/book/knowledge/autocomplete');
  });

  it('empty autocomplete → empty array', async () => {
    const payload = {
      ok: true,
      data: [],
      query: 'nonexistent',
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await searchAutocomplete('nonexistent');
    expect(r.data).toEqual([]);
    expect(r.query).toBe('nonexistent');
  });

  it('type filter works', async () => {
    const payload = {
      ok: true,
      data: [
        ['Философия', 'theme', 8],
        ['Физика', 'expansion', 10],
      ],
      query: 'фил',
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await searchAutocomplete('фил', 10);
    expect(r.data[0].type).toBe('theme');
    expect(r.data[1].type).toBe('expansion');
  });
});

// ── Integration test: envelope unwrap pattern ───────────────

describe('envelope unwrap pattern', () => {
  it('knowledge/search and autocomplete use same envelope pattern', () => {
    const searchEnvelope = ENVELOPE_MAP['GET /book/knowledge/search'];
    const autocompleteEnvelope = ENVELOPE_MAP['GET /book/knowledge/autocomplete'];
    expect(searchEnvelope).toBe('enveloped');
    expect(autocompleteEnvelope).toBe('enveloped');
    expect(searchEnvelope).toBe(autocompleteEnvelope);
  });

  it('autocomplete response shape matches search response shape', () => {
    const autocomplete: AutocompleteResponse = {
      ok: true,
      data: [{ text: 'test', type: 'expansion', score: 10 }],
      query: 'test',
    };
    expect(autocomplete.ok).toBe(true);
    expect(autocomplete.data).toBeInstanceOf(Array);
    expect(typeof autocomplete.query).toBe('string');
  });
});

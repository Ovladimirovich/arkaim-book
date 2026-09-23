/**
 * analytics.test.ts — контракт analytics endpoints (MVP).
 * Проверяет envelope map и типовую структуру ответов.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getReaderHistoryStats,
  getReadingProgress,
} from '@/shared/api/contracts/reader';
import { getGraphStats } from '@/shared/api/contracts/knowledge';
import { getWorldSummary } from '@/shared/api/contracts/world';
import { getCacheStats } from '@/shared/api/contracts/book';
import { listDocuments } from '@/shared/api/contracts/book';

afterEach(() => {
  fetchMock.mockReset();
});

describe('GET /book/reader/history/stats', () => {
  it('enveloped → {questions, sessions, last_active}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, data: { questions: 42, sessions: 5, last_active: '2026-09-17T12:00:00Z' } }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getReaderHistoryStats();
    expect(r.questions).toBe(42);
    expect(r.sessions).toBe(5);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/reader/history/stats');
  });
});

describe('GET /book/graph/stats', () => {
  it('direct → {nodes, edges, node_types, relationship_types}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          nodes: 1036,
          edges: 258,
          node_types: { concept: 852, person: 125 },
          relationship_types: { friend: 502 },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getGraphStats();
    expect(r.nodes).toBe(1036);
    expect(r.edges).toBe(258);
    expect(r.node_types.concept).toBe(852);
  });
});

describe('GET /book/world/summary', () => {
  it('direct → {summary, stats.world_model}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          summary: 'World Engine: 524 сущностей',
          stats: {
            world_model: {
              total_entities: 524,
              total_categories: 13,
              by_category: { philosophy: 268, language: 134 },
            },
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getWorldSummary();
    expect(r.stats.world_model.total_entities).toBe(524);
    expect(r.stats.world_model.total_categories).toBe(13);
    expect(r.stats.world_model.by_category.philosophy).toBe(268);
  });
});

describe('GET /book/cache/stats', () => {
  it('enveloped → {genome, chunks, world_model, api, rag}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          data: {
            genome: { hits: 10, misses: 2, evictions: 0, size: 50, hit_rate: '83%' },
            chunks: { hits: 100, misses: 5, evictions: 0, size: 200, hit_rate: '95%' },
            world_model: { hits: 30, misses: 3, evictions: 0, size: 80, hit_rate: '91%' },
            api: { hits: 500, misses: 10, evictions: 0, size: 1000, hit_rate: '98%' },
            rag: { hits: 200, misses: 15, evictions: 0, size: 300, hit_rate: '93%' },
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getCacheStats();
    expect(r.genome.hits).toBe(10);
    expect(r.chunks.hit_rate).toBe('95%');
    expect(r.rag.misses).toBe(15);
  });
});

describe('GET /book/os/documents', () => {
  it('direct → Document[]', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify([
          { id: 'doc-1', title: 'test.txt', type: 'primary_source', version: '1.0.0', imported_at: '2026-09-17T00:00:00Z', hash: 'abc123' },
        ]),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await listDocuments();
    expect(r.length).toBe(1);
    expect(r[0].title).toBe('test.txt');
  });
});

describe('GET /book/reader/reading-progress', () => {
  it('direct → {data, stats}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          data: [
            {
              chapter_id: 'ch_02',
              chapter_index: 2,
              first_read_at: '2026-07-12T23:05:24Z',
              last_read_at: '2026-07-12T23:05:24Z',
              read_seconds: 45,
              completed: false,
              scroll_percent: 0.5,
            },
          ],
          stats: { chapters_started: 1, chapters_completed: 0, total_seconds: 45 },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getReadingProgress();
    expect(r.stats.chapters_started).toBe(1);
    expect(r.stats.total_seconds).toBe(45);
    expect(r.data[0].chapter_id).toBe('ch_02');
  });
});

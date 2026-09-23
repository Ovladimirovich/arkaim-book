/**
 * reader.test.ts — reader-контракты (F2_SPEC §4, §11-3).
 * Ответы = фактический live-JSON backend (F2-аудит шаг 0).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getReaderProfile,
  getReaderHistory,
  recordReadingEvent,
  getReadingProgress,
  getReadingPosition,
} from '@/shared/api/contracts/reader';

const ok = (data: unknown, extra: Record<string, unknown> = {}) =>
  new Response(JSON.stringify({ ok: true, data, ...extra }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' } as Record<string, string>,
  });

afterEach(() => {
  fetchMock.mockReset();
});

describe('GET /book/reader/profile', () => {
  it('direct → ReaderProfile с topics (после ask — live-факт)', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          reader_id: 'd46d182d',
          display_name: 'f2_step0',
          questions_total: 1,
          conversation_count: 1,
          last_topic: 'Кали Юга',
          topics: [{ name: 'Кали Юга', depth: 0.3, questions: 1 }],
        }),
        { status: 200 },
      ),
    );
    const p = await getReaderProfile();
    expect(p.questions_total).toBe(1);
    expect(p.last_topic).toBe('Кали Юга');
    expect(p.topics![0].depth).toBeGreaterThan(0);
  });
});

describe('GET /book/reader/history', () => {
  it('enveloped → data[] (пустой для /book/ask-пользователя — контракт conversations)', async () => {
    fetchMock.mockResolvedValue(ok([], { total: 0 }));
    const h = await getReaderHistory(5);
    expect(h).toEqual([]);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/reader/history?limit=5');
  });

  it('enveloped → данные, если пользователь общался через /v1-чат', async () => {
    fetchMock.mockResolvedValue(
      ok([{ id: 1, session_id: 's1', content: 'Что такое Кали Юга?', created_at: '2026-09-09T02:00:00Z' }], { total: 1 }),
    );
    const h = await getReaderHistory(50);
    expect(h[0].content).toContain('Кали Юга');
  });
});

describe('POST /book/reader/reading-event', () => {
  it('enveloped {ok:true} — поля Body-контракта', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    const r = await recordReadingEvent({
      chapter_id: 'ch_01',
      chapter_index: 1,
      read_seconds: 42,
      scroll_percent: 55.5,
      completed: false,
    });
    expect(r.ok).toBe(true);
    const body = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(body.chapter_id).toBe('ch_01');
    expect(body.read_seconds).toBe(42);
    expect(body.scroll_percent).toBe(55.5);
  });
});

describe('GET /book/reader/reading-progress', () => {
  it('direct-конверт: data[] + stats В КОНВЕРТЕ (live-факт шага 0)', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          data: [
            {
              chapter_id: 'ch_01',
              chapter_index: 1,
              first_read_at: '2026-09-09T02:32:51Z',
              last_read_at: '2026-09-09T02:32:51Z',
              read_seconds: 42,
              completed: false,
              scroll_percent: 55.5,
            },
          ],
          stats: { chapters_started: 1, chapters_completed: 0, total_seconds: 42 },
        }),
        { status: 200 },
      ),
    );
    const p = await getReadingProgress();
    expect(p.data).toHaveLength(1);
    expect(p.data[0].chapter_id).toBe('ch_01');
    expect(p.stats.chapters_started).toBe(1);
    expect(p.stats.total_seconds).toBe(42);
  });
});

describe('GET /book/reader/reading-position', () => {
  it('enveloped → позиция (продолжить чтение)', async () => {
    fetchMock.mockResolvedValue(
      ok({ chapter_id: 'ch_01', chapter_index: 1, scroll_percent: 55.5, last_read_at: '2026-09-09T02:32:51Z' }),
    );
    const pos = await getReadingPosition();
    expect(pos?.chapter_id).toBe('ch_01');
    expect(pos?.scroll_percent).toBe(55.5);
  });

  it('enveloped → null (новый читатель ещё не читал)', async () => {
    fetchMock.mockResolvedValue(ok(null));
    const pos = await getReadingPosition();
    expect(pos).toBeNull();
  });
});

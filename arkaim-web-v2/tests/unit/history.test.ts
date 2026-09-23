/**
 * history.test.ts — контракт reader history endpoints (F5).
 * Проверяет envelope map и типовую структуру ответов.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getReaderHistorySessions,
  getReaderHistoryFull,
  type ReaderSessionItem,
  type ReaderHistoryFullItem,
} from '@/shared/api/contracts/reader';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ──────────────────────────────────────────

describe('ENVELOPE_MAP — history endpoints', () => {
  it('history/sessions — enveloped', () => {
    expect(ENVELOPE_MAP['GET /book/reader/history/sessions']).toBe('enveloped');
  });

  it('history/full — enveloped', () => {
    expect(ENVELOPE_MAP['GET /book/reader/history/full']).toBe('enveloped');
  });
});

// ── GET /book/reader/history/sessions ─────────────────────

describe('GET /book/reader/history/sessions', () => {
  it('enveloped → ReaderSessionItem[]', async () => {
    const payload = {
      ok: true,
      data: [
        {
          session_id: 'sess-001',
          created_at: '2026-09-17T10:00:00Z',
          question_count: 5,
          last_question_at: '2026-09-17T10:30:00Z',
        },
        {
          session_id: 'sess-002',
          created_at: '2026-09-18T08:00:00Z',
          question_count: 3,
        },
      ],
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getReaderHistorySessions();
    expect(r).toHaveLength(2);
    expect(r[0].session_id).toBe('sess-001');
    expect(r[0].question_count).toBe(5);
    expect(r[1].question_count).toBe(3);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/reader/history/sessions');
  });

  it('пустой массив допустим', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true, data: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getReaderHistorySessions();
    expect(r).toEqual([]);
  });
});

// ── GET /book/reader/history/full ─────────────────────────

describe('GET /book/reader/history/full', () => {
  it('enveloped → ReaderHistoryFullItem[] с limit', async () => {
    const payload = {
      ok: true,
      data: [
        {
          id: 1,
          session_id: 'sess-001',
          content: 'Вопрос о мире Аркаима',
          created_at: '2026-09-17T10:00:00Z',
        },
      ],
    };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getReaderHistoryFull({ limit: 20, session_id: 'sess-001' });
    expect(r).toHaveLength(1);
    expect(r[0].content).toBe('Вопрос о мире Аркаима');
    expect(fetchMock.mock.calls[0][0]).toContain('/book/reader/history/full');
    expect(fetchMock.mock.calls[0][0]).toContain('limit=20');
    expect(fetchMock.mock.calls[0][0]).toContain('session_id=sess-001');
  });

  it('без параметров — без query string', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true, data: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await getReaderHistoryFull();
    expect(fetchMock.mock.calls[0][0]).toBe('/book/reader/history/full');
  });

  it('session_id=null — не добавляет параметр', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true, data: [] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    await getReaderHistoryFull({ limit: 50, session_id: null });
    const url = fetchMock.mock.calls[0][0];
    expect(url).not.toContain('session_id');
    expect(url).toContain('limit=50');
  });
});

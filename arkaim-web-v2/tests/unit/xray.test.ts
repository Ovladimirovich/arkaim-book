/**
 * xray.test.ts — контракт X-Ray endpoints (F5).
 * Проверяет envelope map и типовую структуру ответов.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getXrayVersion,
  getXrayStats,
  getXrayEvents,
  type XrayVersion,
  type XrayStats,
  type XrayEventItem,
} from '@/shared/api/contracts/xray';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ──────────────────────────────────────────

describe('ENVELOPE_MAP — xray endpoints', () => {
  it('все xray-ключи есть в карте', () => {
    expect(ENVELOPE_MAP['GET /xray/events/stream']).toBe('direct');
    expect(ENVELOPE_MAP['GET /xray/stats']).toBe('direct');
    expect(ENVELOPE_MAP['GET /xray/events']).toBe('direct');
    expect(ENVELOPE_MAP['GET /xray/version']).toBe('direct');
  });

  it('все xray-endpoints — direct (raw JSON, не enveloped)', () => {
    const xrayKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('/xray/'));
    for (const key of xrayKeys) {
      expect(ENVELOPE_MAP[key]).toBe('direct');
    }
  });
});

// ── GET /xray/version ─────────────────────────────────────

describe('GET /xray/version', () => {
  it('direct → XrayVersion', async () => {
    const payload: XrayVersion = { version: '0.5.0', build: 'abc123' };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getXrayVersion();
    expect(r.version).toBe('0.5.0');
    expect(r.build).toBe('abc123');
    expect(fetchMock.mock.calls[0][0]).toBe('/xray/version');
  });
});

// ── GET /xray/stats ───────────────────────────────────────

describe('GET /xray/stats', () => {
  it('direct → XrayStats', async () => {
    const payload: XrayStats = { active_traces: 3, completed_traces: 142 };
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getXrayStats();
    expect(r.active_traces).toBe(3);
    expect(r.completed_traces).toBe(142);
    expect(fetchMock.mock.calls[0][0]).toBe('/xray/stats');
  });

  it('пустые трейсы не ломают парсинг', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ active_traces: 0, completed_traces: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getXrayStats();
    expect(r.active_traces).toBe(0);
    expect(r.completed_traces).toBe(0);
  });
});

// ── GET /xray/events ──────────────────────────────────────

describe('GET /xray/events', () => {
  it('direct → XrayEventItem[]', async () => {
    const payload: XrayEventItem[] = [
      {
        trace_id: 'tr-001',
        event: 'trace_completed',
        timestamp: '2026-09-18T10:00:00Z',
        duration_ms: 1234,
        name: 'render_scene',
      },
      {
        trace_id: 'tr-002',
        event: 'trace_frozen',
        timestamp: '2026-09-18T10:01:00Z',
      },
    ];
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getXrayEvents(10);
    expect(r).toHaveLength(2);
    expect(r[0].trace_id).toBe('tr-001');
    expect(r[0].duration_ms).toBe(1234);
    expect(r[1].event).toBe('trace_frozen');
    expect(fetchMock.mock.calls[0][0]).toContain('/xray/events');
    expect(fetchMock.mock.calls[0][0]).toContain('limit=10');
  });

  it('пустой массив допустим', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const r = await getXrayEvents();
    expect(r).toEqual([]);
  });
});

/**
 * presence.test.ts — контракт presence API (F4, F4_SPEC §3.2).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  listPresenceSuggestions,
  getPresenceStats,
  getPresenceTrending,
  approvePresence,
  rejectPresence,
  type PresenceSuggestion,
  type PresenceStats,
  type TrendingItem,
} from '@/shared/api/contracts/presence';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ───────────────────────────────────────────

describe('ENVELOPE_MAP — presence endpoints', () => {
  const presenceKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('/book/presence/'));

  it('все presence-ключи есть в карте', () => {
    expect(presenceKeys).toContain('GET /book/presence/suggestions');
    expect(presenceKeys).toContain('GET /book/presence/suggestions/stats');
    expect(presenceKeys).toContain('POST /book/presence/suggestions/{suggestion_id}/approve');
    expect(presenceKeys).toContain('POST /book/presence/suggestions/{suggestion_id}/reject');
    expect(presenceKeys).toContain('GET /book/presence/trending');
  });

  it('GET presence — enveloped; POST approve/reject — direct', () => {
    expect(ENVELOPE_MAP['GET /book/presence/suggestions']).toBe('enveloped');
    expect(ENVELOPE_MAP['GET /book/presence/suggestions/stats']).toBe('enveloped');
    expect(ENVELOPE_MAP['GET /book/presence/trending']).toBe('enveloped');
    expect(ENVELOPE_MAP['POST /book/presence/suggestions/{suggestion_id}/approve']).toBe('direct');
    expect(ENVELOPE_MAP['POST /book/presence/suggestions/{suggestion_id}/reject']).toBe('direct');
  });
});

// ── GET /book/presence/suggestions ─────────────────────────

describe('GET /book/presence/suggestions', () => {
  it('enveloped → {ok, data: PresenceSuggestion[]}', async () => {
    const payload = {
      ok: true,
      data: [
        { id: 's-1', topic: 'Философия', content: 'Текст предложения', source: 'observer', status: 'pending', created_at: '2026-09-18T00:00:00Z' },
      ],
    };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await listPresenceSuggestions();
    expect(r).toHaveLength(1);
    expect(r[0].id).toBe('s-1');
    expect(r[0].topic).toBe('Философия');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/presence/suggestions');
  });
});

// ── GET /book/presence/suggestions/stats ───────────────────

describe('GET /book/presence/suggestions/stats', () => {
  it('enveloped → {ok, data: PresenceStats}', async () => {
    const payload = { ok: true, data: { total: 10, pending: 3, approved: 5, rejected: 2 } };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await getPresenceStats();
    expect(r.total).toBe(10);
    expect(r.pending).toBe(3);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/presence/suggestions/stats');
  });
});

// ── GET /book/presence/trending ────────────────────────────

describe('GET /book/presence/trending', () => {
  it('enveloped → {ok, data: TrendingItem[]}', async () => {
    const payload = { ok: true, data: [{ topic: 'Архитектура', count: 5, score: 0.9 }] };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await getPresenceTrending();
    expect(r).toHaveLength(1);
    expect(r[0].topic).toBe('Архитектура');
  });
});

// ── POST approve/reject ────────────────────────────────────

describe('POST /book/presence/suggestions/{id}/approve', () => {
  it('direct → {ok: true, suggestion_id}', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true, suggestion_id: 's-1' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await approvePresence('s-1');
    expect(r.ok).toBe(true);
    expect(r.suggestion_id).toBe('s-1');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/presence/suggestions/s-1/approve');
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');
  });
});

describe('POST /book/presence/suggestions/{id}/reject', () => {
  it('direct → {ok: true, suggestion_id}', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true, suggestion_id: 's-2' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await rejectPresence('s-2');
    expect(r.ok).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/presence/suggestions/s-2/reject');
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');
  });
});

/**
 * drafts.test.ts — контракт drafts approve API (F4, F4_SPEC §3.4).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import { listDrafts, approveDraft, type Draft } from '@/shared/api/contracts/drafts';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ───────────────────────────────────────────

describe('ENVELOPE_MAP — drafts endpoints', () => {
  it('все drafts-ключи есть в карте', () => {
    expect(ENVELOPE_MAP).toHaveProperty('GET /book/drafts');
    expect(ENVELOPE_MAP).toHaveProperty('POST /book/drafts/{draft_id}/approve');
  });

  it('GET — enveloped; POST approve — direct', () => {
    expect(ENVELOPE_MAP['GET /book/drafts']).toBe('enveloped');
    expect(ENVELOPE_MAP['POST /book/drafts/{draft_id}/approve']).toBe('direct');
  });
});

// ── GET /book/drafts ───────────────────────────────────────

describe('GET /book/drafts', () => {
  it('enveloped → {ok, data: Draft[]}', async () => {
    const payload: { ok: boolean; data: Draft[] } = {
      ok: true,
      data: [{ id: 'd-1', type: 'content', topic: 'Статья', content: 'Текст черновика', status: 'pending', created_at: '2026-09-18T00:00:00Z' }],
    };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await listDrafts('pending');
    expect(r).toHaveLength(1);
    expect(r[0].topic).toBe('Статья');
    expect(fetchMock.mock.calls[0][0]).toContain('/book/drafts');
  });

  it('без status — все черновики', async () => {
    const payload = { ok: true, data: [] };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    await listDrafts();
    expect(fetchMock.mock.calls[0][0]).toBe('/book/drafts');
  });
});

// ── POST /book/drafts/{id}/approve ─────────────────────────

describe('POST /book/drafts/{id}/approve', () => {
  it('direct → {ok, status, draft_id}', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true, status: 'approved', draft_id: 'd-1' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await approveDraft('d-1');
    expect(r.ok).toBe(true);
    expect(r.status).toBe('approved');
    expect(r.draft_id).toBe('d-1');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/drafts/d-1/approve');
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');
  });
});

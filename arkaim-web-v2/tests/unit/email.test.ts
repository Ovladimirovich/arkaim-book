/**
 * email.test.ts — контракт email API (F4, F4_SPEC §3.3).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  listEmailDrafts,
  sendEmailDraft,
  getEmailStats,
  type EmailDraft,
  type EmailStats,
} from '@/shared/api/contracts/email';
import { ENVELOPE_MAP } from '@/shared/api/envelope';

afterEach(() => {
  fetchMock.mockReset();
});

// ── Envelope map ───────────────────────────────────────────

describe('ENVELOPE_MAP — email endpoints', () => {
  it('все email-ключи есть в карте', () => {
    expect(ENVELOPE_MAP).toHaveProperty('GET /book/email/drafts');
    expect(ENVELOPE_MAP).toHaveProperty('POST /book/email/draft/{draft_id}/send');
    expect(ENVELOPE_MAP).toHaveProperty('GET /book/email/stats');
    expect(ENVELOPE_MAP).toHaveProperty('GET /book/email/draft/auto');
    expect(ENVELOPE_MAP).toHaveProperty('GET /book/email/draft/topic/{topic}');
  });

  it('GET email — enveloped; POST send — direct', () => {
    expect(ENVELOPE_MAP['GET /book/email/drafts']).toBe('enveloped');
    expect(ENVELOPE_MAP['GET /book/email/stats']).toBe('enveloped');
    expect(ENVELOPE_MAP['POST /book/email/draft/{draft_id}/send']).toBe('direct');
  });
});

// ── GET /book/email/drafts ─────────────────────────────────

describe('GET /book/email/drafts', () => {
  it('enveloped → {ok, data: EmailDraft[]}', async () => {
    const payload: { ok: boolean; data: EmailDraft[] } = {
      ok: true,
      data: [{ id: 'e-1', topic: 'Еженедельник', subject: 'Итоги недели', body: 'Текст...', status: 'draft', created_at: '2026-09-18T00:00:00Z' }],
    };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await listEmailDrafts();
    expect(r).toHaveLength(1);
    expect(r[0].topic).toBe('Еженедельник');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/email/drafts');
  });
});

// ── GET /book/email/stats ──────────────────────────────────

describe('GET /book/email/stats', () => {
  it('enveloped → {ok, data: EmailStats}', async () => {
    const payload = { ok: true, data: { sent: 42, pending: 3, subscribers: 150 } };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(payload), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await getEmailStats();
    expect(r.sent).toBe(42);
    expect(r.subscribers).toBe(150);
  });
});

// ── POST /book/email/draft/{id}/send ───────────────────────

describe('POST /book/email/draft/{id}/send', () => {
  it('direct → {ok, draft_id}', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true, draft_id: 'e-1' }), { status: 200, headers: { 'Content-Type': 'application/json' } }));
    const r = await sendEmailDraft('e-1');
    expect(r.ok).toBe(true);
    expect(r.draft_id).toBe('e-1');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/email/draft/e-1/send');
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST');
  });
});

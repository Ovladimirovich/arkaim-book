/**
 * contracts/email.ts — typed-контракты email API (F4, F4_SPEC §3.3).
 *
 * Фактические backend response bodies (forensic audit 2026-09-18):
 *   GET  /book/email/drafts                    → enveloped {ok, data: EmailDraft[]}
 *   POST /book/email/drafts/{id}/send           → direct {ok, draft_id}
 *   GET  /book/email/stats                     → enveloped {ok, data: {sent, pending, subscribers}}
 *   GET  /book/email/draft/auto                → enveloped {ok, data: EmailDraft}
 *   GET  /book/email/draft/topic/{topic}       → enveloped {ok, data: EmailDraft}
 *
 * RBAC: reader+ для чтения; editor+ для send.
 */

import { apiCall } from '../client';

// ── Types ──────────────────────────────────────────────────

export interface EmailDraft {
  id: string;
  topic: string;
  subject: string;
  body: string;
  status: 'draft' | 'sent' | 'scheduled';
  created_at: string;
  sent_at?: string;
}

export interface EmailStats {
  sent: number;
  pending: number;
  subscribers: number;
}

// ── Functions ──────────────────────────────────────────────

/** GET /book/email/drafts */
export function listEmailDrafts(): Promise<EmailDraft[]> {
  return apiCall('GET', '/book/email/drafts');
}

/** POST /book/email/drafts/{id}/send — editor+ */
export function sendEmailDraft(id: string): Promise<{ ok: boolean; draft_id: string }> {
  return apiCall('POST', `/book/email/drafts/${id}/send`, {
    method: 'POST',
    body: {},
  });
}

/** GET /book/email/stats */
export function getEmailStats(): Promise<EmailStats> {
  return apiCall('GET', '/book/email/stats');
}

/** GET /book/email/draft/auto */
export function getAutoDraft(): Promise<EmailDraft> {
  return apiCall('GET', '/book/email/draft/auto');
}

/** GET /book/email/draft/topic/{topic} */
export function getTopicDraft(topic: string): Promise<EmailDraft> {
  return apiCall('GET', `/book/email/draft/topic/${encodeURIComponent(topic)}`);
}

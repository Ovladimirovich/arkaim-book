/**
 * contracts/drafts.ts — typed-контракты drafts approve API (F4, F4_SPEC §3.4).
 *
 * Фактические backend response bodies (forensic audit 2026-09-18):
 *   GET  /book/drafts                  → enveloped {ok, data: Draft[]}
 *   POST /book/drafts/{draft_id}/approve → direct {ok, status: 'approved', draft_id}
 *
 * RBAC: reader+ для чтения; editor+ для approve.
 */

import { apiCall } from '../client';

// ── Types ──────────────────────────────────────────────────

export interface Draft {
  id: string;
  type: string;
  topic: string;
  content: string;
  status: 'pending' | 'approved';
  created_at: string;
  approved_at?: string;
}

// ── Functions ──────────────────────────────────────────────

/** GET /book/drafts?status=pending */
export function listDrafts(status?: string): Promise<Draft[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : '';
  return apiCall('GET', `/book/drafts${q}`);
}

/** POST /book/drafts/{draft_id}/approve — editor+ */
export function approveDraft(draftId: string): Promise<{ ok: boolean; status: string; draft_id: string }> {
  return apiCall('POST', `/book/drafts/${draftId}/approve`, {
    method: 'POST',
    body: {},
  });
}

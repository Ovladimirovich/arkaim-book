/**
 * contracts/presence.ts — typed-контракты presence API (F4, F4_SPEC §3.2).
 *
 * Фактические backend response bodies (forensic audit 2026-09-18):
 *   GET  /book/presence/suggestions          → enveloped {ok, data: PresenceSuggestion[], total}
 *   GET  /book/presence/suggestions/stats    → enveloped {ok, data: {total, pending, approved, rejected}}
 *   GET  /book/presence/suggestions/{id}/view     → enveloped {ok, data: PresenceSuggestion}
 *   POST /book/presence/suggestions/{id}/approve → direct {ok, suggestion_id}
 *   POST /book/presence/suggestions/{id}/reject  → direct {ok, suggestion_id}
 *   GET  /book/presence/trending             → enveloped {ok, data: TrendingItem[]}
 *
 * RBAC: reader+ для чтения; editor+ для approve/reject.
 */

import { apiCall } from '../client';

// ── Types ──────────────────────────────────────────────────

export interface PresenceSuggestion {
  id: string;
  topic: string;
  content: string;
  source: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  score?: number;
}

export interface PresenceStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

export interface TrendingItem {
  topic: string;
  count: number;
  score: number;
}

// ── Functions ──────────────────────────────────────────────

/** GET /book/presence/suggestions */
export function listPresenceSuggestions(): Promise<PresenceSuggestion[]> {
  return apiCall('GET', '/book/presence/suggestions');
}

/** GET /book/presence/suggestions/stats */
export function getPresenceStats(): Promise<PresenceStats> {
  return apiCall('GET', '/book/presence/suggestions/stats');
}

/** GET /book/presence/suggestions/{id}/view */
export function getPresenceSuggestion(id: string): Promise<PresenceSuggestion> {
  return apiCall('GET', `/book/presence/suggestions/${id}/view`);
}

/** POST /book/presence/suggestions/{id}/approve — editor+ */
export function approvePresence(id: string): Promise<{ ok: boolean; suggestion_id: string }> {
  return apiCall('POST', `/book/presence/suggestions/${id}/approve`, {
    method: 'POST',
    body: {},
  });
}

/** POST /book/presence/suggestions/{id}/reject — editor+ */
export function rejectPresence(id: string): Promise<{ ok: boolean; suggestion_id: string }> {
  return apiCall('POST', `/book/presence/suggestions/${id}/reject`, {
    method: 'POST',
    body: {},
  });
}

/** GET /book/presence/trending */
export function getPresenceTrending(): Promise<TrendingItem[]> {
  return apiCall('GET', '/book/presence/trending');
}

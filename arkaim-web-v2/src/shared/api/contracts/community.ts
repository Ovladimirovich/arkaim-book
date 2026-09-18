/**
 * contracts/community.ts — typed-контракты community API (reader+).
 *
 * Фактические backend response bodies (forensic audit 2026-09-18):
 *   GET /book/community/timeline        → direct {events: [{year, title, type}]}
 *   GET /book/community/interpretations → direct {interpretations: [], count}
 *   GET /book/community/interpretations/mine → direct {interpretations: []}
 *   GET /book/community/interpretations/stats → direct {total, pending, approved, rejected}
 *   POST /book/community/interpretations → direct {ok, interpretation}
 *   GET /book/community/artifacts       → direct {artifacts: [], count}
 *   GET /book/community/artifacts/mine  → direct {artifacts: []}
 *   GET /book/community/artifacts/stats → direct {total, pending, approved, categories}
 *   POST /book/community/artifacts      → direct {ok, artifact}
 *   GET /book/community/search?q=       → direct {interpretations: [], artifacts: [], total}
 *   GET /book/community/notifications   → direct {notifications: [], count, unread_count}
 *   GET /book/community/notifications/unread-count → direct {count}
 *   GET /book/community/knowledge/status → direct {modules, module_count, knowledge_dir}
 *
 * Все ответы — raw JSON (direct), ни один не обёрнут в {ok, data}.
 */

import { apiCall } from '../client';

// ── Types ──────────────────────────────────────────────────

export interface CommunityEvent {
  year: string;
  title: string;
  /** civilization | city | migration | event */
  type: string;
}

export interface CommunityTimelineResponse {
  events: CommunityEvent[];
}

export interface CommunityInterpretation {
  id: string;
  reader_id: string;
  reader_name: string;
  text: string;
  themes: string[];
  characters: string[];
  status: string;
  likes: number;
  created_at: string;
}

export interface CommunityInterpretationsResponse {
  interpretations: CommunityInterpretation[];
  count: number;
}

export interface CommunityInterpretationsStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
}

export interface CommunityArtifact {
  id: string;
  reader_id: string;
  reader_name: string;
  title: string;
  description: string;
  category: string;
  source: string;
  connection_to_book: string;
  related_themes: string[];
  related_characters: string[];
  location: string;
  url: string;
  status: string;
  likes: number;
  created_at: string;
}

export interface CommunityArtifactsResponse {
  artifacts: CommunityArtifact[];
  count: number;
}

export interface CommunityArtifactsStats {
  total: number;
  pending: number;
  approved: number;
  categories: Record<string, number>;
}

export interface CommunitySearchResponse {
  interpretations: CommunityInterpretation[];
  artifacts: CommunityArtifact[];
  total: number;
}

export interface CommunityKnowledgeStatus {
  modules: string[];
  module_count: number;
  /** INTERNAL — не показывать в UI */
  knowledge_dir: string;
}

// ── Functions ──────────────────────────────────────────────

/** GET /book/community/timeline */
export function getCommunityTimeline(): Promise<CommunityTimelineResponse> {
  return apiCall('GET', '/book/community/timeline');
}

/** GET /book/community/interpretations/stats */
export function getInterpretationsStats(): Promise<CommunityInterpretationsStats> {
  return apiCall('GET', '/book/community/interpretations/stats');
}

/** GET /book/community/artifacts/stats */
export function getArtifactsStats(): Promise<CommunityArtifactsStats> {
  return apiCall('GET', '/book/community/artifacts/stats');
}

/** GET /book/community/knowledge/status */
export function getKnowledgeStatus(): Promise<CommunityKnowledgeStatus> {
  return apiCall('GET', '/book/community/knowledge/status');
}

/** GET /book/community/search?q= */
export function searchCommunity(q: string): Promise<CommunitySearchResponse> {
  return apiCall('GET', `/book/community/search?q=${encodeURIComponent(q)}`);
}

/** POST /book/community/interpretations */
export function submitInterpretation(req: {
  text: string;
  themes?: string[];
  characters?: string[];
}): Promise<{ ok: boolean; interpretation: CommunityInterpretation }> {
  return apiCall('POST', '/book/community/interpretations', {
    method: 'POST',
    body: req,
  });
}

/** POST /book/community/artifacts */
export function submitArtifact(req: {
  title: string;
  description: string;
  category: string;
  source: string;
  connection_to_book: string;
  related_themes?: string[];
  related_characters?: string[];
  location?: string;
  url?: string;
}): Promise<{ ok: boolean; artifact: CommunityArtifact }> {
  return apiCall('POST', '/book/community/artifacts', {
    method: 'POST',
    body: req,
  });
}

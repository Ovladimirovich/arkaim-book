/**
 * contracts/knowledge.ts — Knowledge Graph API (reader+).
 *
 * Live-факт (2026-09-15):
 *   GET /book/graph/stats       → direct {nodes, edges, node_types, relationship_types}
 *   GET /book/knowledge/search  → enveloped {ok, data: [{topic, score, data:{graph_links,cross_references,...}}], total}
 *
 * Note: graph/search returns enveloped (standard), graph/stats is direct.
 */

import { apiCall } from '../client';

// ── GET /book/graph/stats ─────────────────────────────────

export interface GraphStatsNodeTypes {
  [type: string]: number;
}

export interface GraphStatsRelationshipTypes {
  [type: string]: number;
}

export interface GraphStats {
  nodes: number;
  edges: number;
  node_types: GraphStatsNodeTypes;
  relationship_types: GraphStatsRelationshipTypes;
}

export function getGraphStats(): Promise<GraphStats> {
  return apiCall('GET', '/book/graph/stats');
}

// ── GET /book/knowledge/search ────────────────────────────

export interface KnowledgeSearchResult {
  topic: string;
  score: number;
  data: {
    topic: string;
    content: string;
    cross_references: string[];
    graph_links: string[];
    metadata?: Record<string, unknown>;
    [k: string]: unknown;
  };
}

export interface KnowledgeSearchResponse {
  ok: boolean;
  data: KnowledgeSearchResult[];
  query: string;
  type_filter: string;
  total: number;
  offset: number;
  limit: number;
}

export interface KnowledgeSearchRequest {
  q: string;
  limit?: number;
  type?: string;
  sort?: string;
}

export function searchKnowledge(req: KnowledgeSearchRequest): Promise<KnowledgeSearchResponse> {
  const params = new URLSearchParams();
  params.set('q', req.q);
  if (req.limit) params.set('limit', String(req.limit));
  if (req.type) params.set('type', req.type);
  if (req.sort) params.set('sort', req.sort);
  return apiCall('GET', `/book/knowledge/search?${params}`);
}

/**
 * M8/M9 — read-only Knowledge Trace API.
 *
 * Backend route: GET /knowledge/cards/trace/{entity_id}
 * The response is intentionally not enveloped: it is a DTO projection of the
 * existing Knowledge Card, not a new write/query contract.
 */
export type TraceabilityStatus = 'COMPLETE' | 'PARTIAL' | 'UNKNOWN';

export interface KnowledgeTrace {
  entity_id: string;
  status: TraceabilityStatus;
  claims: Array<Record<string, unknown>>;
  evidence: Array<Record<string, unknown>>;
  world: Record<string, unknown>;
  temporal: Array<Record<string, unknown>>;
  conflicts: Array<Record<string, unknown>>;
  reasoning: Array<Record<string, unknown>>;
  corrections: Array<Record<string, unknown>>;
  uncertainty: Record<string, unknown>;
  limitations: string[];
}

export function getKnowledgeTrace(entityId: string): Promise<KnowledgeTrace> {
  return apiCall('GET', `/knowledge/cards/trace/${encodeURIComponent(entityId)}`);
}

// ── GET /book/knowledge/autocomplete ─────────────────────────

// Backend returns data as array of tuples: [text, type, score]
export type AutocompleteRawItem = [text: string, type: 'expansion' | 'theme' | 'character' | 'symbol', score: number];

export interface AutocompleteSuggestion {
  text: string;
  type: 'expansion' | 'theme' | 'character' | 'symbol';
  score: number;
}

export interface AutocompleteResponse {
  ok: boolean;
  data: AutocompleteRawItem[];
  query: string;
}

export interface NormalizedAutocompleteResponse {
  ok: boolean;
  data: AutocompleteSuggestion[];
  query: string;
}

/**
 * Получает автодополнение и нормализует массив-кортежи в объекты.
 * apiCall/unwrap возвращает raw data (envelope stripped),
 * поэтому здесь обрабатываем уже unwrapped данные.
 */
export async function searchAutocomplete(q: string, limit: number = 8): Promise<NormalizedAutocompleteResponse> {
  const params = new URLSearchParams();
  params.set('q', q);
  params.set('limit', String(limit));
  const raw = await apiCall<AutocompleteRawItem[]>('GET', `/book/knowledge/autocomplete?${params}`);
  // raw is the unwrapped data array; wrap into NormalizedAutocompleteResponse
  return {
    ok: true,
    query: q,
    data: raw.map(([text, type, score]) => ({ text, type, score })),
  };
}

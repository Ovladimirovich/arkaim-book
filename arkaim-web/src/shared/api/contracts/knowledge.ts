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
 *
 * Field set mirrors runtime/core/dto/knowledge.py::KnowledgeTraceResponse:
 * claims/evidence/world/temporal/conflicts/reasoning/corrections/lineage,
 * uncertainty/limitations and pagination (offset/limit/totals/next_offset).
 */
export type TraceabilityStatus = 'COMPLETE' | 'PARTIAL' | 'UNKNOWN';

/** Evidence row as projected by _evidence_projection (runtime/core/routes/knowledge_cards.py). */
export interface KnowledgeTraceEvidence {
  source_ref: string;
  chunk_id?: string | null;
  source_title?: string | null;
  status: string;
  evidence_id?: string | null;
  reason?: string | null;
  claim_id?: string | null;
  [k: string]: unknown;
}

export interface KnowledgeTraceEvidenceLink {
  record_id: string;
  source_ref: string;
}

export interface KnowledgeTraceCorrectionLink {
  correction_id: string;
  stale_reasoning_ids: string[];
}

/** Cross-record link as projected by _trace_lineage (built from M5 conflicts only). */
export interface KnowledgeTraceLineageLink {
  conflict_id: string;
  claim_ids: string[];
  evidence_ids: string[];
  claim_links: string[];
  evidence_links: KnowledgeTraceEvidenceLink[];
  reasoning_ids: string[];
  corrections: KnowledgeTraceCorrectionLink[];
  [k: string]: unknown;
}

export interface KnowledgeTraceTotals {
  claims: number;
  evidence: number;
  conflicts: number;
  conflict_notes?: number;
  reasoning: number;
  corrections: number;
  lineage: number;
}

/**
 * Typed World reference (M3 resolver) — mirrors
 * core/CORE/schemas/world_reference.py::WorldEntityReference.
 */
export type WorldReferenceStatus = 'RESOLVED' | 'UNRESOLVED' | 'AMBIGUOUS' | 'CROSSWALK_UNAPPROVED';

export interface WorldEntityReference {
  query: string;
  canonical_id?: string | null;
  name?: string | null;
  status: WorldReferenceStatus;
  reason?: string;
  resolution_method?: string;
  world_provenance?: Record<string, unknown> | null;
}

/**
 * Typed Temporal reference (M4 resolver) — mirrors
 * core/CORE/schemas/temporal_reference.py::TemporalReference.
 */
export type TemporalReferenceStatus = 'RESOLVED' | 'UNRESOLVED' | 'UNKNOWN';
export type TemporalTimeBasis = 'WORLD_TIME' | 'SOURCE_PUBLICATION' | 'INGESTION' | 'ASSERTION';

export interface TemporalReference {
  claim_id: string;
  time_basis: TemporalTimeBasis;
  status: TemporalReferenceStatus;
  temporal_node_id?: string | null;
  event_id?: string | null;
  era_id?: string | null;
  precision?: string;
  bounds?: Record<string, unknown> | null;
  temporal_provenance?: Array<Record<string, unknown>> | null;
  reason?: string;
  resolution_method?: string;
}

export interface KnowledgeTrace {
  entity_id: string;
  status: TraceabilityStatus;
  claims: Array<Record<string, unknown>>;
  evidence: KnowledgeTraceEvidence[];
  world: Record<string, unknown>;
  world_reference?: WorldEntityReference | null;
  temporal: Array<Record<string, unknown>>;
  temporal_reference?: TemporalReference | null;
  conflicts: Array<Record<string, unknown>>;
  conflict_notes?: Array<Record<string, unknown>>;
  reasoning: Array<Record<string, unknown>>;
  corrections: Array<Record<string, unknown>>;
  lineage?: KnowledgeTraceLineageLink[];
  uncertainty: Record<string, unknown>;
  limitations: string[];
  offset: number;
  limit: number;
  totals: KnowledgeTraceTotals;
  next_offset: number | null;
}

export interface KnowledgeTraceQuery {
  offset?: number;
  limit?: number;
}

export function getKnowledgeTrace(entityId: string, query?: KnowledgeTraceQuery): Promise<KnowledgeTrace> {
  const params = new URLSearchParams();
  if (query?.offset !== undefined) params.set('offset', String(query.offset));
  if (query?.limit !== undefined) params.set('limit', String(query.limit));
  const qs = params.toString();
  return apiCall('GET', `/knowledge/cards/trace/${encodeURIComponent(entityId)}${qs ? `?${qs}` : ''}`);
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

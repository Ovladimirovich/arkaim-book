/**
 * contracts/temporal.ts — typed-контракты «Время мира» (F3, F3_PRE_IMPLEMENTATION_AUDIT §2).
 *
 * Live-факты (F3 шаг 0, TestClient 2026-09-10):
 *   GET /book/temporal/chain   → enveloped {ok, data: {id, label, direction, nodes[],
 *     relations[], gaps, provenance[], confidence, stats}, stats: {nodes, relations, gaps}}
 *   GET /book/temporal/nodes   → enveloped {ok, data: node[], total}
 *     (13 узлов: 12 эпох + temporal_today; today — точка наблюдения, НЕ в цепочке)
 *   GET /book/temporal/context/{epoch_id} → enveloped {ok, data: {temporal_node, epoch,
 *     events[], characters[], technologies[], event_count, character_count, technology_count}}
 *   POST /book/temporal/future-extrapolation → enveloped {ok, data: {anchor_id,
 *     anchor_label, chain_stats, patterns_count, scenarios[], provenance[],
 *     provenance_note}} (reader-гейт; работает без LLM-ключей)
 *   GET /book/temporal/pending-updates          → enveloped {ok, data: finding[], total}
 *   GET /book/temporal/pending-updates/stats    → enveloped {ok, data: {pending, confirmed, rejected}}
 *   GET /book/temporal/pending-updates/history  → enveloped {ok, data: {confirmed[], rejected[]}}
 *   GET /book/temporal/pending-updates/{id}     → enveloped {ok, data: {...finding, status}}
 *   POST /book/temporal/pending-updates/scan    → enveloped {ok, data: {book_changed, ...}}
 *   POST /book/temporal/pending-updates/{id}/confirm  → enveloped {ok, data: {finding_id, applied, manager}}
 *   POST /book/temporal/pending-updates/{id}/reject  → enveloped {ok, data: {finding_id, applied, manager}}
 *
 * Инвариант ADR_TEMPORAL §5 (критический для F3): фронт НЕ синтезирует связи.
 * Отсутствующий relation (Современность → Аркаим) остаётся отсутствующим:
 * цепочка рендерится ТОЛЬКО из data.nodes/data.relations бэкенда.
 */

import { apiCall } from '../client';

// ── Provenance (категории — backend-семантика source_levels.py) ──

export interface ProvenanceTag {
  source_level: string;
  category: string;
  source_url: string | null;
  source_title: string | null;
  confidence: number;
  added_at: string;
  added_by: string;
  notes: string;
}

// ── Узел цепочки ──

export interface TemporalBounds {
  start: string | null;
  end: string | null;
  uncertainty: string | null;
}

export interface TemporalNode {
  id: string;
  label: string;
  precision: string;
  era_id: string;
  entity_ids: string[];
  event_ids: string[];
  provenance: ProvenanceTag[];
  confidence: number;
  bounds: TemporalBounds | null;
  notes: string;
  is_anchor: boolean;
}

export interface TemporalRelation {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  strength: number;
  confidence: number;
  provenance: ProvenanceTag[];
  [k: string]: unknown;
}

export interface TemporalChain {
  id: string;
  label: string;
  direction: string;
  nodes: TemporalNode[];
  relations: TemporalRelation[];
  gaps: unknown[];
  provenance: ProvenanceTag[];
  confidence: number;
  stats: { nodes: number; relations: number; gaps: number };
}

export function getTemporalChain(direction?: 'FORWARD' | 'BACKWARD'): Promise<TemporalChain> {
  const q = direction ? `?direction=${direction}` : '';
  return apiCall('GET', `/book/temporal/chain${q}`);
}

export function getTemporalNodes(): Promise<TemporalNode[]> {
  return apiCall('GET', '/book/temporal/nodes');
}

// ── Контекст эпохи ──

export interface TemporalEvent {
  id: string;
  name?: string;
  title: string;
  title_ru: string;
  description?: string;
  epoch?: string;
  location_id?: string;
  characters_involved?: string[];
  [k: string]: unknown;
}

export interface TemporalCharacter {
  id: string;
  name: string;
  name_ru?: string;
  [k: string]: unknown;
}

export interface TemporalTechnology {
  id: string;
  name: string;
  [k: string]: unknown;
}

export interface TemporalEpoch {
  id: string;
  name: string;
  name_ru: string;
  description: string;
  order: number;
  duration_years: number | null;
  provenance: ProvenanceTag[];
  [k: string]: unknown;
}

export interface TemporalContext {
  temporal_node: TemporalNode;
  epoch: TemporalEpoch;
  events: TemporalEvent[];
  characters: TemporalCharacter[];
  technologies: TemporalTechnology[];
  event_count: number;
  character_count: number;
  technology_count: number;
}

export function getTemporalContext(epochId: string): Promise<TemporalContext> {
  return apiCall('GET', `/book/temporal/context/${epochId}`);
}

// ── Сценарии будущего (M8; reader-гейт; FUTURE_EXTRAPOLATION-бейдж обязателен) ──

export interface FutureScenario {
  description: string;
  compatibility_score: number;
  is_compatible: boolean;
  risk_level: string;
  violations_count: number;
  warnings_count: number;
}

export interface FutureExtrapolationData {
  anchor_id: string;
  anchor_label: string;
  chain_stats: Record<string, number>;
  patterns_count: number;
  scenarios: FutureScenario[];
  provenance: ProvenanceTag[];
  provenance_note: string;
}

export interface FutureExtrapolationRequest {
  prompt: string;
  max_futures?: number;
  anchor_id?: string;
}

export function extrapolateFuture(req: FutureExtrapolationRequest): Promise<FutureExtrapolationData> {
  return apiCall('POST', '/book/temporal/future-extrapolation', { method: 'POST', body: req });
}

// ── Temporal-очередь (M10.2) ──

export interface TemporalFinding {
  id: string;
  kind: string;
  raw_text: string;
  value: string;
  line_number: number;
  context: string;
  category: string;
  confidence: number;
  status?: 'pending' | 'confirmed' | 'rejected';
  reason?: string;
}

export interface QueueStats {
  pending: number;
  confirmed: number;
  rejected: number;
}

export interface QueueHistory {
  confirmed: TemporalFinding[];
  rejected: TemporalFinding[];
}

export function scanBook(): Promise<{
  book_changed: boolean;
  new_findings?: number;
  duplicate_findings?: number;
  total_pending?: number;
}> {
  return apiCall('POST', '/book/temporal/pending-updates/scan', { method: 'POST', body: {} });
}

export function listPending(): Promise<TemporalFinding[]> {
  return apiCall('GET', '/book/temporal/pending-updates');
}

export function getQueueStats(): Promise<QueueStats> {
  return apiCall('GET', '/book/temporal/pending-updates/stats');
}

export function getQueueHistory(): Promise<QueueHistory> {
  return apiCall('GET', '/book/temporal/pending-updates/history');
}

export function getFinding(findingId: string): Promise<TemporalFinding> {
  return apiCall('GET', `/book/temporal/pending-updates/${findingId}`);
}

export function confirmFinding(findingId: string): Promise<{
  finding_id: string;
  applied: boolean;
  manager: QueueStats;
}> {
  return apiCall('POST', `/book/temporal/pending-updates/${findingId}/confirm`, {
    method: 'POST',
    body: {},
  });
}

export function rejectFinding(findingId: string, reason = ''): Promise<{
  finding_id: string;
  applied: boolean;
  manager: QueueStats;
}> {
  return apiCall('POST', `/book/temporal/pending-updates/${findingId}/reject`, {
    method: 'POST',
    body: { reason },
  });
}

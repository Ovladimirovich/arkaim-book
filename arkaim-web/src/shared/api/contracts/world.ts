/**
 * contracts/world.ts — typed-контракты World Engine (F2_SPEC §7, F3_SPEC §world).
 *
 * Live-факты (smoke-test 2026-09-14, порт 8649):
 *   GET  /book/world/summary     → direct {summary, stats: {world_model: {total_categories, total_entities, by_category}}}
 *   GET  /book/world/categories  → direct {categories: {cat: count}, total}
 *   POST /book/world/search      → direct {world_model: entity[], relations: [], total}
 *   GET  /book/world/entity/{id} → direct {category, id, name, name_ru, description, properties, relations}
 *   GET  /book/world/rules       → direct {rules: [{id, name, name_ru, description, description_ru, rule_type, severity}]}
 *   GET  /book/world/modes       → direct {modes: [{mode, name, name_ru, description, description_ru}]}
 *
 * Конверт: direct (без enveloped-ok обёртки) — подтверждено live-фактом.
 */

import { apiCall } from '../client';

// ── GET /book/world/summary ────────────────────────────────

export interface WorldModelStats {
  total_categories: number;
  total_entities: number;
  by_category: Record<string, number>;
}

export interface WorldSummaryStats {
  world_model: WorldModelStats;
  relation_graph?: unknown;
  form_engine?: unknown;
  initialized?: boolean;
}

export interface WorldSummary {
  summary: string;
  stats: WorldSummaryStats;
}

export function getWorldSummary(): Promise<WorldSummary> {
  return apiCall('GET', '/book/world/summary');
}

// ── GET /book/world/categories ─────────────────────────────

export interface WorldCategories {
  categories: Record<string, number>;
  total: number;
}

export function getWorldCategories(): Promise<WorldCategories> {
  return apiCall('GET', '/book/world/categories');
}

// ── POST /book/world/search ────────────────────────────────

export interface WorldEntity {
  id: string;
  name?: string;
  name_ru?: string;
  category?: string;
  strength?: number;
  description?: string;
  [k: string]: unknown;
}

export interface WorldSearchResult {
  world_model: WorldEntity[];
  relations: unknown[];
  total: number;
}

export interface WorldSearchRequest {
  query: string;
  limit?: number;
}

export function searchWorld(req: WorldSearchRequest): Promise<WorldSearchResult> {
  return apiCall('POST', '/book/world/search', { method: 'POST', body: req });
}

// ── GET /book/world/entity/{id} ────────────────────────────

export interface WorldEntityDetail extends WorldEntity {
  relations?: unknown[];
  properties?: Record<string, unknown>;
}

export function getWorldEntity(entityId: string): Promise<WorldEntityDetail> {
  return apiCall('GET', `/book/world/entity/${encodeURIComponent(entityId)}`);
}

// ── GET /book/world/rules ──────────────────────────────────

export interface WorldRule {
  id: string;
  name: string;
  name_ru: string;
  description: string;
  description_ru: string;
  rule_type: string;
  severity: string;
}

export function getWorldRules(): Promise<{ rules: WorldRule[] }> {
  return apiCall('GET', '/book/world/rules');
}

// ── GET /book/world/modes ──────────────────────────────────

export interface WorldMode {
  mode: string;
  name: string;
  name_ru: string;
  description: string;
  description_ru: string;
}

export function getWorldModes(): Promise<{ modes: WorldMode[] }> {
  return apiCall('GET', '/book/world/modes');
}

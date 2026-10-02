/**
 * contracts/world.ts — typed-контракты World Engine.
 */

import { apiCall } from '../client';

export interface WorldProvenanceStatus {
  status: 'available' | 'missing';
  source_level?: string | null;
  source_category?: string | null;
  source?: string | null;
  source_file?: string | null;
  notes?: string | null;
  confidence?: number | null;
}

export type WorldEntityProvenance = WorldProvenanceStatus;

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

export interface WorldCategories {
  categories: Record<string, number>;
  total: number;
}

export function getWorldCategories(): Promise<WorldCategories> {
  return apiCall('GET', '/book/world/categories');
}

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

export interface WorldEntityDetail extends WorldEntity {
  relations?: unknown[];
  properties?: Record<string, unknown>;
  provenance?: WorldEntityProvenance;
}

export function getWorldEntity(entityId: string): Promise<WorldEntityDetail> {
  return apiCall('GET', `/book/world/entity/${encodeURIComponent(entityId)}`);
}

export interface WorldEntityContext {
  entity: WorldEntityDetail;
  relations: {
    outgoing_count: number;
    incoming_count: number;
    outgoing: unknown[];
    incoming: unknown[];
  };
}

export function getWorldEntityContext(entityId: string): Promise<WorldEntityContext> {
  return apiCall('GET', `/book/world/entity/${encodeURIComponent(entityId)}/context`);
}

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
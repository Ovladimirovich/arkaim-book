/**
 * contracts/worldExplorer.ts — typed-контракты World Explorer («Исследование мира»).
 *
 * Live-факты (backend: core/CORE/narrative_engine/api_routes.py, router prefix /world-explorer,
 * подключён в book_routes.py → монтируется на /book):
 *   POST /book/world-explorer/explore                  → enveloped {data: ExplorationResult}
 *   POST /book/world-explorer/explore/hypothesis       → enveloped {data: ExplorationResult}
 *   POST /book/world-explorer/validate                 → enveloped {data: CompatibilityResult}
 *   GET  /book/world-explorer/epochs                   → enveloped {data: Epoch[]}
 *   GET  /book/world-explorer/stats                    → enveloped {data: WorldExplorerStats}
 *   GET  /book/world-explorer/hypotheses/{epoch_id}    → enveloped {data: Hypothesis[]}
 *   GET  /book/world-explorer/possibilities/{epoch_id} → enveloped {data: Possibility[]}
 *   GET  /book/world-explorer/history                  → enveloped {data: HistoryItem[]}
 *   GET  /book/world-explorer/history/{exploration_id} → enveloped {data: HistoryItem}
 *   GET  /book/world-explorer/feedback                 → enveloped {data: unknown[]}
 *   POST /book/world-explorer/history                  → direct   {ok, id}        (нет data)
 *   POST /book/world-explorer/feedback                 → direct   {ok, id}        (нет data)
 *   DELETE /book/world-explorer/history/{id}           → direct   {ok}           (нет data)
 *   POST /book/world-explorer/generate-from-branch     → enveloped {data: ...}
 *
 * Конверт: см. ENVELOPE_MAP (enveloped для GET/основных, direct для POST/DELETE без data).
 */

import { apiCall } from '../client';

// ── Справочники ────────────────────────────────────────────

export interface Epoch {
  id: string;
  name: string;
  name_ru: string;
  order: number;
}

export interface WorldExplorerStats {
  world_model: string;
  patterns_count: number;
  epochs_count: number;
  locations_count: number;
  events_count: number;
}

// ── Совместимость (validate) ──────────────────────────────

export interface CompatibilityAxis {
  axis: string;
  score: number;
  violations_count: number;
  warnings_count: number;
}

export interface CompatibilityResult {
  overall_score: number;
  is_compatible: boolean;
  risk_level: string;
  axis_scores: CompatibilityAxis[];
  violations_count: number;
  warnings_count: number;
  recommendations: string[];
}

// ── Гипотезы / возможности ─────────────────────────────────

export interface Hypothesis {
  id: string;
  title: string;
  description: string;
  type: string;
  epoch?: string;
  confidence?: number;
  tags?: string[];
}

export interface Possibility {
  id?: string;
  title?: string;
  title_ru?: string;
  description?: string;
  category?: string;
  confidence?: number;
  tags?: string[];
  [k: string]: unknown;
}

// ── Результат исследования ────────────────────────────────

export interface RankedBranch {
  rank: number;
  branch_type: string;
  title: string;
  quality_score: number;
  quality_summary?: string;
  strengths: string[];
  weaknesses: string[];
  impact_score: number;
  contradictions: number;
  delta_changes: number;
}

export interface ExplorationResult {
  request: { prompt: string; epoch?: string; location?: string; branch_count: number };
  hypothesis: Hypothesis | null;
  scenario: { branch_count: number; best_branch_id: string; summary: string };
  ranked_branches: RankedBranch[];
  duration_ms: number;
  summary: string;
}

export interface HistoryItem {
  id: number;
  prompt: string;
  epoch?: string | null;
  hypothesis_title?: string | null;
  summary?: string;
  overall_score?: number;
  branch_count_actual?: number;
  duration_ms?: number;
  created_at?: string;
  /** При запросе детали (GET /history/{id}) сюда распаковывается result_json. */
  result?: ExplorationResult;
  [k: string]: unknown;
}

// ── Запросы ───────────────────────────────────────────────

export interface ExploreRequest {
  prompt: string;
  epoch?: string;
  branch_count?: number;
}

export interface ValidateRequest {
  prompt: string;
  epoch?: string;
  location?: string;
}

export interface SaveHistoryRequest {
  prompt: string;
  epoch?: string | null;
  branch_count?: number;
  hypothesis_id?: string | null;
  hypothesis_title?: string | null;
  result_json: string;
  summary?: string;
  overall_score?: number;
  branch_count_actual?: number;
  duration_ms?: number;
}

export interface FeedbackRequest {
  exploration_id?: number | null;
  branch_rank: number;
  branch_type: string;
  branch_title: string;
  rating: number;
  comment?: string;
}

export interface GenerateFromBranchRequest {
  exploration_prompt: string;
  branch_title: string;
  branch_type: string;
  epoch?: string;
  location?: string;
  style?: string;
  max_length?: number;
  quality_score?: number;
  strengths?: string[];
  weaknesses?: string[];
}

export interface GeneratedBranchText {
  system_instruction: string;
  user_prompt: string;
  style?: string;
  max_length?: number;
  branch_title?: string;
  quality_score?: number;
  constraints_summary?: string;
}

// ── API-функции ────────────────────────────────────────────

/** Полный pipeline: совместимость → гипотезы → сценарии → влияние → ранжирование. */
export function exploreWorld(req: ExploreRequest): Promise<ExplorationResult> {
  return apiCall('POST', '/book/world-explorer/explore', { body: req, timeoutMs: 120_000 });
}

/** Исследовать от конкретной гипотезы (эпоха + branch_count). */
export function exploreFromHypothesis(
  hypothesisId: string,
  epoch: string,
  branchCount = 3,
): Promise<ExplorationResult> {
  return apiCall(
    'POST',
    `/book/world-explorer/explore/hypothesis?hypothesis_id=${encodeURIComponent(hypothesisId)}&epoch=${encodeURIComponent(epoch)}&branch_count=${branchCount}`,
    { timeoutMs: 120_000 },
  );
}

/** Проверка идеи на совместимость с каноном (6 осей). */
export function validateIdea(req: ValidateRequest): Promise<CompatibilityResult> {
  return apiCall('POST', '/book/world-explorer/validate', { body: req });
}

/** Список эпох, доступных для исследования. */
export function getExplorerEpochs(): Promise<Epoch[]> {
  return apiCall('GET', '/book/world-explorer/epochs');
}

/** Статистика World Explorer (мир, паттерны, эпохи, локации, события). */
export function getExplorerStats(): Promise<WorldExplorerStats> {
  return apiCall('GET', '/book/world-explorer/stats');
}

/** Гипотезы для эпохи. */
export function getHypotheses(epochId: string, limit = 10): Promise<Hypothesis[]> {
  return apiCall('GET', `/book/world-explorer/hypotheses/${encodeURIComponent(epochId)}?limit=${limit}`);
}

/** Возможности для эпохи. */
export function getPossibilities(epochId: string, limit = 10): Promise<Possibility[]> {
  return apiCall('GET', `/book/world-explorer/possibilities/${encodeURIComponent(epochId)}?limit=${limit}`);
}

/** История исследований текущего пользователя. */
export function getExplorationHistory(limit = 50): Promise<HistoryItem[]> {
  return apiCall('GET', `/book/world-explorer/history?limit=${limit}`);
}

/** Полная запись исследования (result_json распакован в result). */
export function getExplorationDetail(id: number): Promise<HistoryItem> {
  return apiCall('GET', `/book/world-explorer/history/${id}`);
}

/** Сохранить результат исследования в историю (ответ: {ok, id}). */
export function saveExploration(req: SaveHistoryRequest): Promise<{ ok: boolean; id: number }> {
  return apiCall('POST', '/book/world-explorer/history', { body: req });
}

/** Удалить запись истории (ответ: {ok}). */
export function deleteExploration(id: number): Promise<{ ok: boolean }> {
  return apiCall('DELETE', `/book/world-explorer/history/${id}`);
}

/** Отправить оценку ветви (ответ: {ok, id}). */
export function submitFeedback(req: FeedbackRequest): Promise<{ ok: boolean; id: number }> {
  return apiCall('POST', '/book/world-explorer/feedback', { body: req });
}

/** Сформировать промпт для LLM на основе ветви. */
export function generateFromBranch(req: GenerateFromBranchRequest): Promise<GeneratedBranchText> {
  return apiCall('POST', '/book/world-explorer/generate-from-branch', { body: req, timeoutMs: 120_000 });
}

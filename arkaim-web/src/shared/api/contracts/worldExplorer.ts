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
 *   POST /book/world-explorer/hypothesis/{id}/accept    → enveloped {data: ...}
 *   POST /book/world-explorer/hypothesis/{id}/reject    → enveloped {data: ...}
 *   GET  /book/world-explorer/scenarios                 → enveloped {data: ScenarioSummary[]}
 *   POST /book/world-explorer/scenario/{id}/supersede   → enveloped {data: ScenarioDecision}
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
  /** proposed / accepted / rejected / superseded (Этап 5, lifecycle). */
  status?: string;
}

/** Решение автора по гипотезе. Система сама accept/reject не выполняет. */
export interface HypothesisDecision {
  hypothesis_id: string;
  status: string;
  decided_at?: string;
  reason?: string;
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

// ── Сценарии (lifecycle, Этап 6b) ──────────────────────────

/** Сценарий из хранилища вместе с его lifecycle-статусом. */
export interface ScenarioSummary {
  id: string;
  hypothesis_id: string;
  title: string;
  title_ru: string;
  description: string;
  branch_type: string;
  quality_score: number;
  tags: string[];
  /** Количество изменений мира (WorldDelta.total_changes). */
  changes: number;
  /** proposed / accepted / rejected / superseded. */
  status: string;
  /** id сценария, которым заменён этот (пусто, если не заменён). */
  superseded_by: string;
  proposed_at: string;
  decided_at: string;
  decision_note: string;
}

/** Результат замены сценария. Исходный остаётся в истории. */
export interface ScenarioDecision {
  scenario_id: string;
  status: string;
  superseded_by: string;
}

/** Параметры списка сценариев. */
export interface ScenarioListParams {
  hypothesisId?: string;
  limit?: number;
  /** true — вернуть и заменённые/отклонённые (историю решений). */
  includeHistory?: boolean;
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

// ── Глубокое исследование ───────────────────────────────────

export interface DeepExplorationRequest {
  prompt: string;
  epoch?: string;
  parent_branch_id?: string;
  max_depth?: number;
  branches_per_level?: number;
}

export interface DeepExplorationNode {
  id: string;
  hypothesis: Hypothesis;
  scenario?: {
    branch_count: number;
    best_branch_id: string;
    summary: string;
  };
  quality_report?: {
    overall_score: number;
    summary: string;
    strengths: string[];
    weaknesses: string[];
  };
  children: string[];
  parent_id: string;
  depth: number;
  quality_score: number;
}

export interface DeepExplorationTree {
  root_node: DeepExplorationNode | null;
  nodes: Record<string, DeepExplorationNode>;
  total_nodes: number;
  max_depth_reached: number;
  summary: string;
}

export interface DeepExplorationResponse {
  ok: boolean;
  data: {
    total_nodes: number;
    max_depth: number;
    summary: string;
    nodes: Record<string, DeepExplorationNode>;
  };
}

// ── Свободные точки мира ────────────────────────────────────

export interface FreePoint {
  id: string;
  title: string;
  description: string;
  epoch?: string;
  category: string;
  confidence: number;
}

export interface FreePointsResponse {
  ok: boolean;
  data: FreePoint[];
  count: number;
}

// ── Лучшие пути ─────────────────────────────────────────────

export interface BestPath {
  nodes: string[];
  total_score: number;
}

export interface BestPathsResponse {
  ok: boolean;
  data: BestPath[];
  message?: string;
}

// ── Unified Pipeline ────────────────────────────────────────

export interface UnifiedRequest {
  prompt: string;
  epoch?: string;
  location?: string;
  branch_count?: number;
  style?: string;
  max_length?: number;
  generate_story?: boolean;
  select_best?: boolean;
}

export interface UnifiedResponse {
  ok: boolean;
  data: {
    exploration: {
      branch_count: number;
      best_score: number;
      summary: string;
    } | null;
    story: {
      system_instruction: string;
      user_prompt: string;
      style: string;
      constraints_summary: string;
    } | null;
    selected_branch_rank: number;
    pipeline_steps: string[];
    duration_ms: number;
  };
  summary: string;
}

// ── Экспорт результатов ─────────────────────────────────────

export interface ExportRequest {
  prompt: string;
  epoch?: string;
  branch_count?: number;
}

export interface ExportResponse {
  ok: boolean;
  data: {
    title: string;
    created_at: string;
    prompt: string;
    epoch: string | null;
    branch_count: number;
    best_score: number;
    duration_ms: number;
    branches_summary: string;
    recommendations: string[];
    markdown: string;
  };
}

// ── Статистика кэша ─────────────────────────────────────────

export interface CacheStatsResponse {
  ok: boolean;
  data: {
    caches: Record<string, unknown>;
    performance_metrics: Record<string, unknown>;
  };
}

// ── API-функции для недостающих возможностей ────────────────

export function deepExplore(req: DeepExplorationRequest): Promise<DeepExplorationResponse> {
  return apiCall('POST', '/book/world-explorer/explore-deep', { body: req, timeoutMs: 120_000 });
}

export function getFreePoints(epoch?: string): Promise<FreePointsResponse> {
  const qs = epoch ? `?epoch=${encodeURIComponent(epoch)}` : '';
  return apiCall('GET', `/book/world-explorer/free-points${qs}`);
}

export function getBestPaths(treeId: string = 'root', topN: number = 3): Promise<BestPathsResponse> {
  return apiCall('GET', `/book/world-explorer/best-paths?tree_id=${encodeURIComponent(treeId)}&top_n=${topN}`);
}

export function unifiedPipeline(req: UnifiedRequest): Promise<UnifiedResponse> {
  return apiCall('POST', '/book/world-explorer/unified', { body: req, timeoutMs: 120_000 });
}

export function exportResults(req: ExportRequest): Promise<ExportResponse> {
  return apiCall('POST', '/book/world-explorer/export', { body: req, timeoutMs: 120_000 });
}

export function getWorldExplorerCacheStats(): Promise<CacheStatsResponse> {
  return apiCall('GET', '/book/world-explorer/cache/stats');
}

export function clearCache(): Promise<{ ok: boolean; message: string }> {
  return apiCall('POST', '/book/world-explorer/cache/clear');
}

export function searchExternalSources(query: string, limit?: number, sources?: string): Promise<{
  ok: boolean;
  data: unknown[];
  count: number;
  sources_searched: string[];
}> {
  const qs = `?query=${encodeURIComponent(query)}&limit=${limit ?? 5}${sources ? `&sources=${sources}` : ''}`;
  return apiCall('GET', `/book/world-explorer/sources/search${qs}`);
}

export function getFeedbackList(limit = 50): Promise<{ ok: boolean; data: unknown[]; count: number }> {
  return apiCall('GET', `/book/world-explorer/feedback?limit=${limit}`);
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

/** Принять гипотезу — явное решение автора (мир автоматически не меняется). */
export function acceptHypothesis(hypothesisId: string): Promise<HypothesisDecision> {
  return apiCall(
    'POST',
    `/book/world-explorer/hypothesis/${encodeURIComponent(hypothesisId)}/accept`,
  );
}

/** Отклонить гипотезу: запись остаётся в истории со статусом rejected. */
export function rejectHypothesis(
  hypothesisId: string,
  reason = '',
): Promise<HypothesisDecision> {
  return apiCall(
    'POST',
    `/book/world-explorer/hypothesis/${encodeURIComponent(hypothesisId)}/reject`,
    { body: { reason } },
  );
}

/** Список сценариев с их статусом (по умолчанию — только активные). */
export function getScenarios(
  params: ScenarioListParams = {},
): Promise<ScenarioSummary[]> {
  const qs = new URLSearchParams();
  if (params.hypothesisId) qs.set('hypothesis_id', params.hypothesisId);
  if (typeof params.limit === 'number') qs.set('limit', String(params.limit));
  if (params.includeHistory) qs.set('include_history', 'true');
  const query = qs.toString();
  return apiCall(
    'GET',
    `/book/world-explorer/scenarios${query ? `?${query}` : ''}`,
  );
}

/** Заменить сценарий: исходный сохраняется в истории как superseded. */
export function supersedeScenario(
  scenarioId: string,
  supersededBy: string,
  reason = '',
): Promise<ScenarioDecision> {
  return apiCall(
    'POST',
    `/book/world-explorer/scenario/${encodeURIComponent(scenarioId)}/supersede`,
    { body: { superseded_by: supersededBy, reason } },
  );
}

/** Сформировать промпт для LLM на основе ветви. */
export function generateFromBranch(req: GenerateFromBranchRequest): Promise<GeneratedBranchText> {
  return apiCall('POST', '/book/world-explorer/generate-from-branch', { body: req, timeoutMs: 120_000 });
}

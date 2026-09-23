/**
 * contracts/book.ts — typed-контракты книги (F2_SPEC §4).
 *
 * Response-schema у book-endpoint'ов в OpenAPI пустые ({}) либо SuccessResponse,
 * поэтому типы фиксируются ЗДЕСЬ по ФАКТИЧЕСКОМУ live-JSON (F2-аудит шаг 0):
 *   POST /book/ask        → enveloped {data: AskAnswer}
 *   POST /v1/stream       → SSE text/event-stream (не enveloped, raw stream)
 *   GET  /book/chapters   → enveloped {data: Chapter[]}
 *   GET  /book/chapters/{chapter_id} → enveloped {data: ChapterContent}
 *   GET  /book/text       → enveloped {data: string, offset, limit, total, has_more}
 *   GET  /book/layers     → direct {knowledge_layer, meaning_layer, identity_layer, mission_layer, world_engine_layer}
 *   GET  /book/genome     → direct BookGenomeResponse
 */

import { apiCall } from '../client';

// ── POST /book/ask ─────────────────────────────────────

export interface AskRequest {
  question: string;
  /** Опциональный контекст диалога (строка, собранная приложением). */
  context?: string;
  /** Опциональная история сообщений (OpenAI-совместимая). */
  messages?: Array<{ role: string; content: string }>;
}

export interface ProvenanceItem {
  type: string;
  /** Присутствует не всегда: у theme — name, у rag — source. */
  name?: string;
  source?: string;
}

/** Live-факт (шаг 0): mood/suggestion присутствуют, но опциональны. */
export interface AskAnswer {
  answer: string;
  source: string;
  provenance?: ProvenanceItem[];
  pulse_confidence?: number;
  llm_used?: boolean;
  mood?: string;
  suggestion?: string;
}

export function ask(req: AskRequest): Promise<AskAnswer> {
  return apiCall('POST', '/book/ask', { method: 'POST', body: req, timeoutMs: 60_000 });
}

/**
 * Streaming-чат через POST /v1/stream.
 * Не использует apiCall (SSE stream, не JSON response).
 * Возвращает Promise, который разрешается когда stream завершён.
 * Вызывающий сам управляет накоплением текста через onToken.
 */
export interface StreamAskOptions {
  messages?: Array<{ role: string; content: string }>;
  session_id?: string;
  onToken?: (token: string) => void;
  onDone?: () => void;
  onError?: (err: unknown) => void;
  signal?: AbortSignal;
}

export async function streamAsk(opts: StreamAskOptions): Promise<void> {
  const { consumeSseResponse } = await import('@/shared/realtime/sse');
  const body = {
    messages: opts.messages ?? [],
    session_id: opts.session_id,
    stream: true,
  };
  const resp = await fetch('/v1/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(body),
    signal: opts.signal,
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`HTTP ${resp.status}: ${text.slice(0, 300)}`);
  }
  let doneCalled = false;
  await consumeSseResponse(resp, {
    onEvent: (e) => {
      const d = e.data as Record<string, unknown>;
      if (typeof d?.text === 'string') {
        opts.onToken?.(d.text);
      }
    },
    onDone: () => {
      doneCalled = true;
      opts.onDone?.();
    },
    onError: (err) => {
      if (!doneCalled) opts.onError?.(err);
    },
    signal: opts.signal,
  });
}

// ── GET /book/chapters ─────────────────────────────────

export interface Chapter {
  id: string;
  title: string;
  char_count: number;
  index: number;
}

export interface ChapterContent {
  id: string;
  chapter_id: string;
  title: string;
  index: number;
  content: string;
}

export function getChapters(): Promise<Chapter[]> {
  return apiCall('GET', '/book/chapters');
}

export function getChapter(chapterId: string): Promise<ChapterContent> {
  return apiCall('GET', `/book/chapters/${chapterId}`);
}

// ── GET /book/text (пагинация) ─────────────────────────

export interface TextResponse {
  data: string;
  offset: number;
  limit: number;
  total: number;
  has_more: boolean;
}

export function getText(offset: number, limit = 4000): Promise<TextResponse> {
  return apiCall('GET', `/book/text?offset=${offset}&limit=${limit}`);
}

// ── GET /book/layers ───────────────────────────────────

export interface BookLayers {
  knowledge_layer: string;
  meaning_layer: string;
  identity_layer: string;
  mission_layer: string;
  world_engine_layer: string;
}

export function getLayers(): Promise<BookLayers> {
  return apiCall('GET', '/book/layers');
}

// ── GET /book/genome ───────────────────────────────────

export interface GenomeAuthorIntent {
  title: string;
  description: string;
  main_message?: string;
  questions_for_reader?: string[];
}

export interface GenomeTheme {
  id: string;
  name: string;
  description: string;
  strength: number;
  questions: number;
}

export interface GenomeCharacter {
  id: string;
  name: string;
  type: string;
  archetype: string;
  aliases: string[];
  description: string;
  strength: number;
}

export interface GenomeValue {
  id: string;
  name: string;
  description: string;
  strength: number;
}

export interface GenomeWorldEntity {
  name: string;
  type: string;
  description: string;
  values: string[];
  related_to: string[];
}

export interface BookGenome {
  themes: GenomeTheme[];
  characters: GenomeCharacter[];
  values: GenomeValue[];
  world_entities: GenomeWorldEntity[];
  author_intent?: GenomeAuthorIntent;
  modules?: Record<string, unknown>;
}

/**
 * ВНИМАНИЕ (F2_SPEC §7): genome доступен БЕЗ can()-гейта —
 * суффикс-коллизия RBAC-матрицы (F1-аудит §3); backend сам авторизует (reader).
 */
export function getGenome(): Promise<BookGenome> {
  return apiCall('GET', '/book/genome');
}

// ── GET /book/os/documents + POST /book/os/pipeline/ingest ────────────
// BookOS document management (editor+ for ingest, reader+ for list).

/** Фактический ответ Document (schemas.document.py + to_dict). */
export interface Document {
  id: string;
  title: string;
  type: 'primary_source' | 'secondary_source' | 'external';
  version: string;
  imported_at: string;
  hash: string;
  path?: string;
  chunks_count?: number;
}

/** Фактический ответ IngestionOrchestrator.ingest() (orchestrator.py:170). */
export interface IngestResult {
  status: 'ok' | 'error';
  document_id?: string;
  title?: string;
  hash?: string;
  chunks_count?: number;
  entities_added?: number;
  facts_added?: number;
  relationships_added?: number;
  chunks_indexed?: number;
  errors?: string[];
}

/**
 * GET /book/os/documents — список загруженных документов.
 * Requires: reader (GET /book/os/documents — editor in RBAC matrix).
 */
export function listDocuments(doc_type?: string): Promise<Document[]> {
  const params = doc_type ? `?doc_type=${encodeURIComponent(doc_type)}` : '';
  return apiCall('GET', `/book/os/documents${params}`);
}

/**
 * DELETE /book/os/documents/{doc_id} — удалить документ из хранилища.
 * Requires: editor.
 */
export function deleteDocument(doc_id: string): Promise<{ deleted: string }> {
  return apiCall('DELETE', `/book/os/documents/${doc_id}`);
}

// ── GET /book/cache/stats (analytics) ─────────────────────

export interface CacheStatsEntry {
  hits: number;
  misses: number;
  evictions: number;
  size: number;
  hit_rate: string;
}

export interface CacheStats {
  genome: CacheStatsEntry;
  chunks: CacheStatsEntry;
  world_model: CacheStatsEntry;
  api: CacheStatsEntry;
  rag: CacheStatsEntry;
}

export function getCacheStats(): Promise<CacheStats> {
  return apiCall('GET', '/book/cache/stats');
}

/**
 * POST /book/os/pipeline/ingest — полный конвейер загрузки документа.
 * Multipart/form-data (field: 'file') — нельзя через apiCall (JSON body).
 * Requires: editor.
 */
export async function uploadDocument(
  file: File,
  doc_type: string = 'primary_source',
  version: string = '1.0.0',
): Promise<IngestResult> {
  const params = new URLSearchParams({ doc_type, version });
  const resp = await fetch(`/book/os/pipeline/ingest?${params}`, {
    method: 'POST',
    credentials: 'same-origin',
    body: (() => { const fd = new FormData(); fd.append('file', file); return fd; })(),
  });
  if (!resp.ok) {
    let detail = `Ошибка загрузки (HTTP ${resp.status})`;
    try {
      const body = await resp.json();
      const d = (body as Record<string, unknown>).detail;
      if (typeof d === 'string') detail = d;
      else if (Array.isArray(d) && d[0]?.msg) detail = String(d[0].msg);
    } catch { /* ignore */ }
    throw new Error(detail);
  }
  return resp.json() as Promise<IngestResult>;
}

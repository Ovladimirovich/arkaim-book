/**
 * contracts/reader.ts — typed-контракты читателя (F2_SPEC §4).
 *
 * Live-факты (F2-аудит шаг 0):
 *   GET /book/reader/profile   → direct ReaderProfileResponse
 *   GET /book/reader/history   → enveloped {ok, data: [...], total}
 *     ⚠️ читает conversations-таблицу, которую /book/ask НЕ заполняет:
 *     для читателя, работающего через /book/ask, история пуста — это
 *     backend-архитектура (красная линия F2), НЕ дефект фронтенда.
 *   POST /book/reader/reading-event → enveloped {ok}
 *   GET /book/reader/reading-progress → enveloped {data, stats}
 *   GET /book/reader/reading-position → enveloped {data: position|null}
 */

import { apiCall } from '../client';

// ── profile ────────────────────────────────────────────

export interface ReaderTopicItem {
  name: string;
  depth: number;
  questions: number;
}

export interface ReaderProfile {
  reader_id: string;
  display_name: string;
  questions_total: number;
  conversation_count: number;
  last_topic: string;
  topics?: ReaderTopicItem[];
}

export function getReaderProfile(): Promise<ReaderProfile> {
  return apiCall('GET', '/book/reader/profile');
}

// ── history (контракт сохранён; фактические данные — см. док-комментарий) ──

export interface ReaderHistoryItem {
  id: number;
  session_id: string;
  content: string;
  created_at: string;
}

export function getReaderHistory(limit = 50): Promise<ReaderHistoryItem[]> {
  return apiCall('GET', `/book/reader/history?limit=${limit}`);
}

// ── reading-event / progress / position ────────────────

export interface ReadingEventRequest {
  chapter_id: string;
  chapter_index: number;
  read_seconds: number;
  scroll_percent: number;
  completed: boolean;
}

/**
 * Live-факт (шаг 0): конверт {ok: true} БЕЗ data-поля — endpoint помечен
 * 'direct' в ENVELOPE_MAP, контракт читает конверт целиком.
 */
export function recordReadingEvent(req: ReadingEventRequest): Promise<{ ok: boolean }> {
  return apiCall('POST', '/book/reader/reading-event', { method: 'POST', body: req });
}

export interface ReadingProgressItem {
  chapter_id: string;
  chapter_index: number;
  first_read_at: string;
  last_read_at: string;
  read_seconds: number;
  completed: boolean;
  scroll_percent: number;
}

export interface ReadingStats {
  chapters_started: number;
  chapters_completed: number;
  total_seconds: number;
}

/**
 * Live-факт: stats лежит В КОНВЕРТЕ рядом с data (не внутри data) —
 * поэтому endpoint помечен 'direct' в ENVELOPE_MAP и контракт читает
 * полный конверт.
 */
export interface ReadingProgressEnvelope {
  ok?: boolean;
  data: ReadingProgressItem[];
  stats: ReadingStats;
}

export function getReadingProgress(): Promise<ReadingProgressEnvelope> {
  return apiCall('GET', '/book/reader/reading-progress');
}

export interface ReadingPosition {
  chapter_id: string;
  chapter_index: number;
  scroll_percent: number;
  last_read_at: string;
}

export function getReadingPosition(): Promise<ReadingPosition | null> {
  return apiCall('GET', '/book/reader/reading-position');
}

// ── history/stats (analytics) ────────────────────────────

export interface ReaderHistoryStats {
  questions: number;
  sessions: number;
  last_active: string | null;
}

export function getReaderHistoryStats(): Promise<ReaderHistoryStats> {
  return apiCall('GET', '/book/reader/history/stats');
}

// ── history/sessions (F5) ─────────────────────────────────

export interface ReaderSessionItem {
  session_id: string;
  created_at: string;
  question_count: number;
  last_question_at?: string;
}

export function getReaderHistorySessions(): Promise<ReaderSessionItem[]> {
  return apiCall('GET', '/book/reader/history/sessions');
}

// ── history/full (F5) ────────────────────────────────────

export interface ReaderHistoryFullItem {
  id: number;
  session_id: string;
  content: string;
  created_at: string;
}

export function getReaderHistoryFull(params?: { limit?: number; session_id?: string | null }): Promise<ReaderHistoryFullItem[]> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set('limit', String(params.limit));
  if (params?.session_id !== undefined && params.session_id !== null) qs.set('session_id', params.session_id);
  const query = qs.toString();
  return apiCall('GET', `/book/reader/history/full${query ? `?${query}` : ''}`);
}

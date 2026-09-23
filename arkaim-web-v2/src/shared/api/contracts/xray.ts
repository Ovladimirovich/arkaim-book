/**
 * contracts/xray.ts — typed-контракты X-Ray observability (F5).
 *
 * Live-факт (F5-аудит):
 *   GET /xray/version    → direct {version, build}
 *   GET /xray/stats      → direct {active_traces, completed_traces}
 *   GET /xray/events     → direct XrayEvent[] (последние события)
 *   GET /xray/events/stream → SSE (consumeSseResponse из sse.ts)
 */

import { apiCall } from '../client';

// ── version ──────────────────────────────────────────────

export interface XrayVersion {
  version: string;
  build?: string;
}

export function getXrayVersion(): Promise<XrayVersion> {
  return apiCall('GET', '/xray/version');
}

// ── stats ────────────────────────────────────────────────

export interface XrayStats {
  active_traces: number;
  completed_traces: number;
}

export function getXrayStats(): Promise<XrayStats> {
  return apiCall('GET', '/xray/stats');
}

// ── events (last N) ──────────────────────────────────────

export interface XrayEventItem {
  trace_id: string;
  event: string;
  timestamp: string;
  duration_ms?: number;
  name?: string;
}

export function getXrayEvents(limit = 50): Promise<XrayEventItem[]> {
  return apiCall('GET', `/xray/events?limit=${limit}`);
}

/**
 * realtime/xray-sse.ts — SSE hook для X-Ray live ленты (F5).
 *
 * Использует consumeSseResponse из sse.ts для подписки на
 * GET /xray/events/stream (typed SSE events).
 *
 * Bounded buffer: последние N событий хранятся в ref,
 * не более bufferSize элементов.
 */
'use client';

import { useEffect, useRef, useState } from 'react';
import { consumeSseResponse, type SseEvent } from './sse';

const DEFAULT_BUFFER_SIZE = 100;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30_000;

export type XrayEventType =
  | 'trace_completed'
  | 'trace_frozen'
  | 'trace_terminated'
  | 'orphan_change'
  | 'stats_changed'
  | 'heartbeat';

export interface XrayEventData {
  trace_id?: string;
  name?: string;
  duration_ms?: number;
  count?: number;
  active?: number;
  completed?: number;
}

export interface XraySseMessage {
  event: XrayEventType;
  data: XrayEventData;
  timestamp: number;
}

interface UseXraySseOptions {
  /** Обработчик каждого события. Вызывается синхронно. */
  onEvent: (msg: XraySseMessage) => void;
  /** Макс. размер буфера (по умолчанию 100). */
  bufferSize?: number;
  /** Базовая задержка reconnect (мс, по умолчанию 1000). */
  reconnectBaseMs?: number;
  /** Макс. задержка reconnect (мс, по умолчанию 30000). */
  reconnectMaxMs?: number;
}

/**
 * Подписаться на SSE-ленту /xray/events/stream.
 *
 * Lifecycle:
 *   mount     → fetch + consumeSseResponse
 *   event     → onEvent(msg) + push to buffer
 *   error     → reconnect с exponential backoff
 *   unmount   → abort() + cleanup
 */
export function useXraySse(opts: UseXraySseOptions) {
  const {
    onEvent,
    reconnectBaseMs = RECONNECT_BASE_MS,
    reconnectMaxMs = RECONNECT_MAX_MS,
  } = opts;
  const _bufferSize = opts.bufferSize ?? DEFAULT_BUFFER_SIZE;
  void _bufferSize; // used in useXraySseBuffer wrapper

  const abortRef = useRef<AbortController | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const maxAttempts = 20;

  const connect = () => {
    // Cancel previous connection
    abortRef.current?.abort();
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    fetch('/xray/events/stream', { signal: controller.signal })
      .then((resp) => {
        if (!resp.ok) throw new Error(`SSE HTTP ${resp.status}`);
        attemptRef.current = 0;
        return consumeSseResponse(resp, {
          onEvent: (e: SseEvent) => {
            if (controller.signal.aborted) return;
            try {
              const data = (typeof e.data === 'string' ? JSON.parse(e.data) : e.data) as XrayEventData;
              onEvent({
                event: e.event as XrayEventType,
                data,
                timestamp: Date.now(),
              });
            } catch {
              // non-JSON event data — ignore
            }
          },
          onError: () => {
            if (controller.signal.aborted) return;
            // transient error — reconnect
            scheduleReconnect();
          },
          onDone: () => {
            if (controller.signal.aborted) return;
            scheduleReconnect();
          },
          signal: controller.signal,
        });
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          scheduleReconnect();
        }
      });
  };

  const scheduleReconnect = () => {
    if (attemptRef.current >= maxAttempts) return;
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    attemptRef.current++;
    const delay = Math.min(reconnectBaseMs * Math.pow(2, attemptRef.current - 1), reconnectMaxMs);
    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null;
      connect();
    }, delay);
  };

  useEffect(() => {
    connect();
    return () => {
      abortRef.current?.abort();
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}

export interface UseXraySseBufferOptions {
  /** Обработчик каждого события. */
  onEvent?: (msg: XraySseMessage) => void;
  /** Макс. размер буфера (по умолчанию 100). */
  bufferSize?: number;
  /** Базовая задержка reconnect (мс). */
  reconnectBaseMs?: number;
  /** Макс. задержка reconnect (мс). */
  reconnectMaxMs?: number;
}

/**
 * Хук, возвращающий буфер последних N событий.
 * Используется в UI-компонентах для рендера ленты.
 */
export function useXraySseBuffer(opts: UseXraySseBufferOptions) {
  const bufferSize = opts.bufferSize ?? DEFAULT_BUFFER_SIZE;
  const [buffer, setBuffer] = useState<XraySseMessage[]>([]);

  useXraySse({
    bufferSize,
    reconnectBaseMs: opts.reconnectBaseMs,
    reconnectMaxMs: opts.reconnectMaxMs,
    onEvent: (msg) => {
      setBuffer((prev) => {
        const next = [...prev, msg];
        if (next.length > bufferSize) {
          return next.slice(-bufferSize);
        }
        return next;
      });
      opts.onEvent?.(msg);
    },
  });

  return buffer;
}

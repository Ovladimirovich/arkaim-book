/**
 * sse.ts — примитив потребления SSE-контрактов backend (F1_SPEC §9).
 *
 * Существующие SSE-каналы:
 *   POST /v1/stream            — чат-стрим, кадры "data: {json}" (домен F2)
 *   GET  /xray/events/stream   — типизированные события (event: <name> + data:)
 *
 * F1 доставляет только парсер-примитив; потребителей нет (красная линия).
 * Это разрешённое место сетевых вызовов (eslint).
 */
'use client';

export interface SseEvent {
  event: string;
  data: unknown;
}

export interface SseClientOptions {
  /** Вызывается для каждого события (event-имя + распарсенный data-JSON). */
  onEvent: (e: SseEvent) => void;
  onDone?: () => void;
  onError?: (err: unknown) => void;
  signal?: AbortSignal;
}

/**
 * Прочитать SSE-ответ fetch и разобрать кадры по спецификации W3C:
 *   "event: <name>\ndata: <json>\n\n" (и default "message" без event).
 */
export async function consumeSseResponse(resp: Response, opts: SseClientOptions) {
  const reader = resp.body?.getReader();
  if (!reader) throw new Error('SSE: ответ без тела');
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = 'message';

  const processFrame = (frame: string) => {
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const raw = line.slice(5).trim();
        let data: unknown = raw;
        try {
          data = JSON.parse(raw);
        } catch {
          // не-JSON data — отдаём строкой
        }
        opts.onEvent({ event: currentEvent, data });
        currentEvent = 'message';
      }
      // heartbeat-комментарии ("": / ": keep-alive") игнорируются
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';
      for (const f of frames) processFrame(f);
    }
    if (buffer.trim()) processFrame(buffer);
    opts.onDone?.();
  } catch (e) {
    if (opts.signal?.aborted) return;
    opts.onError?.(e);
  }
}

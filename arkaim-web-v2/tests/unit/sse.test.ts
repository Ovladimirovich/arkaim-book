/**
 * sse.test.ts — SSE-парсер-примитив (F1_SPEC §9): кадры W3C, JSON-data.
 */
import { describe, expect, it } from 'vitest';
import { consumeSseResponse } from '@/shared/realtime/sse';

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const c of chunks) controller.enqueue(encoder.encode(c));
        controller.close();
      },
    }),
    { headers: { 'Content-Type': 'text/event-stream' } },
  );
}

describe('consumeSseResponse', () => {
  it('типизированные кадры: event: + data:', async () => {
    const events: { event: string; data: unknown }[] = [];
    await consumeSseResponse(
      sseResponse(['event: trace_completed\ndata: {"trace_id":"t1"}\n\n', 'event: heartbeat\ndata: {}\n\n']),
      { onEvent: (e) => events.push(e) },
    );
    expect(events).toEqual([
      { event: 'trace_completed', data: { trace_id: 't1' } },
      { event: 'heartbeat', data: {} },
    ]);
  });

  it('кадр без event: → message (контракт /v1/stream)', async () => {
    const events: { event: string; data: unknown }[] = [];
    await consumeSseResponse(sseResponse(['data: {"text":"При"}\n\ndata: {"text":"вет"}\n\n']), {
      onEvent: (e) => events.push(e),
    });
    expect(events.map((e) => e.data)).toEqual([{ text: 'При' }, { text: 'вет' }]);
    expect(events.every((e) => e.event === 'message')).toBe(true);
  });

  it('кадр, разрезанный между чанками, склеивается', async () => {
    const events: { event: string; data: unknown }[] = [];
    await consumeSseResponse(sseResponse(['event: stats_cha', 'nged\ndata: {"a":1}\n\n']), {
      onEvent: (e) => events.push(e),
    });
    expect(events).toEqual([{ event: 'stats_changed', data: { a: 1 } }]);
  });
});

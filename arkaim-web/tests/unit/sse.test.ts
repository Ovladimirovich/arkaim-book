import { describe, expect, it, vi } from 'vitest';
import { consumeSseResponse, type SseEvent } from '@/shared/realtime/sse';

function chunkedResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { headers: { 'content-type': 'text/event-stream' } });
}

describe('consumeSseResponse', () => {
  it('сохраняет text и related_entities даже если JSON-кадр разорван между чанками', async () => {
    const events: SseEvent[] = [];
    const onEvent = vi.fn((event: SseEvent) => events.push(event));
    const onDone = vi.fn();

    await consumeSseResponse(
      chunkedResponse([
        'data: {"text":"Велик — ',
        'герой книги"}\n\n',
        'data: {"related_entities":[{"entity_id":"character_velik",',
        '"entity_type":"character","name":"Велик","description":"Главный герой"}]}\n\ndata: [DONE]\n\n',
      ]),
      { onEvent, onDone },
    );

    expect(onEvent).toHaveBeenCalledTimes(3);
    expect(events[0].data).toEqual({ text: 'Велик — герой книги' });
    expect(events[1].data).toEqual({
      related_entities: [
        {
          entity_id: 'character_velik',
          entity_type: 'character',
          name: 'Велик',
          description: 'Главный герой',
        },
      ],
    });
    expect(events[2].data).toBe('[DONE]');
    expect(onDone).toHaveBeenCalledOnce();
  });
});
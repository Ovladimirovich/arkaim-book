/** audit-sse.mjs — проверка malformed-кадров SSE-парсера (аудит §6). */
async function readResp(chunks) {
  const enc = new TextEncoder();
  return new Response(
    new ReadableStream({
      start(c) {
        for (const ch of chunks) c.enqueue(enc.encode(ch));
        c.close();
      },
    }),
  );
}

const { consumeSseResponse } = await import('../src/shared/realtime/sse.ts');

// 1. битый JSON в data:
const ev1 = [];
await consumeSseResponse(await readResp(['data: {bad json}\n\n']), { onEvent: (e) => ev1.push(e) });
console.log('1. битый JSON: не упал =', ev1.length === 1, '; data передан строкой =', ev1[0]?.data === '{bad json}');

// 2. event: без data: (тихий кадр)
const ev2 = [];
await consumeSseResponse(await readResp(['event: ping\n\n']), { onEvent: (e) => ev2.push(e) });
console.log('2. event без data: событий =', ev2.length, '(0 — кадр тихо проглочен)');

// 3. heartbeat-комментарий + data
const ev3 = [];
await consumeSseResponse(await readResp([': keep-alive\ndata: {"a":1}\n\n']), { onEvent: (e) => ev3.push(e) });
console.log('3. комментарий + data: событий =', ev3.length, '; data =', JSON.stringify(ev3[0]?.data));

// 4. unknown event-имя
const ev4 = [];
await consumeSseResponse(await readResp(['event: totally_unknown\n_data: {"x":1}\n\n']), { onEvent: (e) => ev4.push(e) });
console.log('4. кадр с ":" в начале (не event/data): событий =', ev4.length, '(0 — корректно, поле не распознано)');

// 5. пустой поток
const ev5 = [];
await consumeSseResponse(await readResp(['']), { onEvent: (e) => ev5.push(e) });
console.log('5. пустой поток: onDone без событий, не упал =', ev5.length === 0);
process.exit(0);

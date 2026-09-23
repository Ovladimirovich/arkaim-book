/** f2-step0.mjs — live-проба недоопределённых контрактов (read-only, без правок backend). */
const BASE = 'http://localhost:8642';

async function j(r) { try { return await r.json(); } catch { return '<no json>'; } }

const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `f2_step0_${Date.now()}` }),
});
const cookie = (reg.headers.get('set-cookie') || '').split(';')[0];
console.log('register:', reg.status);

async function probe(method, path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method, headers: { 'Content-Type': 'application/json', cookie },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await j(r);
  console.log(`\n${method} ${path} → ${r.status}`);
  console.log(JSON.stringify(data).slice(0, 500));
  return data;
}

// 1. ask — чтобы в history появилась запись
await probe('POST', '/book/ask', { question: 'Что такое Кали Юга?' });
// 2. history — фактический формат элемента
await probe('GET', '/book/reader/history?limit=5');
// 3. reading-event
await probe('POST', '/book/reader/reading-event', { chapter_id: 'ch_01', chapter_index: 1, read_seconds: 42, scroll_percent: 55.5, completed: false });
// 4. reading-progress / reading-position
await probe('GET', '/book/reader/reading-progress');
await probe('GET', '/book/reader/reading-position');
// 5. layers — полный набор ключей
await probe('GET', '/book/layers');
// 6. genome — ключи верхнего уровня
await probe('GET', '/book/genome');
// 7. profile после ask
await probe('GET', '/book/reader/profile');

/** f2-live-probe.mjs — live-проверка фактических JSON-ответов читательского ядра. */
const BASE = 'http://localhost:8642';

async function j(resp) {
  try { return await resp.json(); } catch { return '<no json>'; }
}

// Сессия (register создаёт reader + cookie)
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `f2_probe_${Date.now()}` }),
});
const cookie = (reg.headers.get('set-cookie') || '').split(';')[0];
console.log('register:', reg.status, '| cookie:', cookie ? 'yes' : 'NO');

async function probe(method, path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', cookie },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await j(r);
  console.log(`\n${method} ${path} → ${r.status}`);
  console.log(JSON.stringify(data).slice(0, 400));
  return data;
}

await probe('GET', '/book/chapters');
await probe('GET', '/book/text?offset=0&limit=200');
await probe('GET', '/book/layers');
await probe('GET', '/book/reader/profile');
await probe('GET', '/book/reader/history?limit=3');
await probe('GET', '/book/genome');
await probe('POST', '/book/ask', { question: 'Кто такой Древний Уст?' });

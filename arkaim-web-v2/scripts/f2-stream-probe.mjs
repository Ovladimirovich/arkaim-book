/** f2-stream-probe.mjs — /v1/stream с читательской cookie (SSE-контракт). */
const BASE = 'http://localhost:8642';

const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `f2_stream_${Date.now()}` }),
});
const cookie = (reg.headers.get('set-cookie') || '').split(';')[0];

const r = await fetch(`${BASE}/v1/stream`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', cookie },
  body: JSON.stringify({ message: 'Привет! Одно предложение о себе.' }),
});
console.log('POST /v1/stream (cookie):', r.status, '| content-type:', r.headers.get('content-type'));
const text = await r.text();
console.log('первые 500 символов SSE-потока:');
console.log(text.slice(0, 500));
console.log('\n— всего строк:', text.split('\n').length);

// /book/ask + SSE? — ask обычный JSON (уже проверен). Смотрим /v1/chat не-SSE:
const r2 = await fetch(`${BASE}/v1/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', cookie },
  body: JSON.stringify({ message: 'Привет!' }),
});
console.log('\nPOST /v1/chat (cookie):', r2.status, JSON.stringify(await r2.json()).slice(0, 200));

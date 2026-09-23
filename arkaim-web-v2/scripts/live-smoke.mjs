/**
 * live-smoke.mjs — live-проверка фактических auth-контрактов backend'а.
 * Запуск при поднятом backend :8642. Печатает статусы/тела/cookie.
 */
const BASE = 'http://localhost:8642';

async function j(resp) {
  try { return await resp.json(); } catch { return '<no json>'; }
}

// 1. /health
const h = await fetch(`${BASE}/health`);
console.log('GET /health:', h.status, JSON.stringify(await j(h)).slice(0, 120));

// 2. /auth/me без сессии
const me0 = await fetch(`${BASE}/auth/me`);
console.log('GET /auth/me (no session):', me0.status, JSON.stringify(await j(me0)).slice(0, 120));

// 3. register → cookie
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `f1_smoke_${Date.now()}` }),
});
const regBody = await j(reg);
console.log('POST /auth/register:', reg.status, JSON.stringify(regBody).slice(0, 160));
const setCookie = reg.headers.get('set-cookie');
console.log('set-cookie:', setCookie ? setCookie.split(';')[0].slice(0, 40) + '...' : 'NONE');

// 4. /auth/me с cookie из register
if (setCookie) {
  const me1 = await fetch(`${BASE}/auth/me`, { headers: { cookie: setCookie.split(';')[0] } });
  console.log('GET /auth/me (session):', me1.status, JSON.stringify(await j(me1)).slice(0, 160));
}

// 5. dev/generate-token (контракт F1 §5; dev-эндпоинт)
const dev = await fetch(`${BASE}/auth/dev/generate-token`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ telegram_user_id: 'smoke-dev', username: 'smoke-dev', display_name: 'Smoke', role: 'admin' }),
});
console.log('POST /auth/dev/generate-token:', dev.status, JSON.stringify(await j(dev)).slice(0, 140));

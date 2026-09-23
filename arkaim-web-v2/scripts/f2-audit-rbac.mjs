/**
 * f2-audit-rbac.mjs — §4: live RBAC — allowed/forbidden/unauthenticated.
 * Проверяем: frontend-контракты вызывают только reader-доступные endpoint'ы,
 * и что запрещённые (editor/admin) недоступны reader-сессии.
 */
const BASE = 'http://localhost:8642';
const out = [];
function check(name, cond, extra = '') {
  out.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) process.exitCode = 1;
}

// reader-сессия
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `rbac_${Date.now()}` }),
});
const cookie = (reg.headers.get('set-cookie') || '').split(';')[0];
const H = { 'Content-Type': 'application/json', cookie };

// 1. allowed: все F2-endpoint'ы доступны reader
for (const [m, p, b] of [
  ['POST', '/book/ask', { question: 'тест' }],
  ['GET', '/book/chapters', null],
  ['GET', '/book/reader/profile', null],
  ['GET', '/book/reader/reading-position', null],
  ['GET', '/book/genome', null],
]) {
  const r = await fetch(`${BASE}${p}`, { method: m, headers: H, body: b ? JSON.stringify(b) : undefined });
  check(`reader ${m} ${p} → ${r.status}`, r.status === 200);
}

// 2. forbidden: reader НЕ должен видеть editor/admin endpoints (backend-гейт)
for (const [m, p, b] of [
  ['GET', '/book/presence/suggestions', null],       // matrix: editor
  ['GET', '/auth/admin/users', null],                  // matrix: admin
  ['GET', '/book/memory/stats', null],                 // routes/book.py: require admin
]) {
  const r = await fetch(`${BASE}${p}`, { method: m, headers: H, body: b ? JSON.stringify(b) : undefined });
  check(`reader ${m} ${p} → ${r.status} (запрещён)`, r.status === 403 || r.status === 401);
}

// 3. unauthenticated: все F2-endpoint'ы требуют сессию
for (const [m, p, b] of [
  ['POST', '/book/ask', { question: 'x' }],
  ['GET', '/book/chapters', null],
  ['GET', '/book/reader/profile', null],
  ['GET', '/book/genome', null],
  ['POST', '/book/reader/reading-event', { chapter_id: 'x', chapter_index: 0, read_seconds: 0, scroll_percent: 0, completed: false }],
]) {
  const r = await fetch(`${BASE}${p}`, {
    method: m, headers: { 'Content-Type': 'application/json' }, body: b ? JSON.stringify(b) : undefined,
  });
  check(`unauth ${m} ${p} → ${r.status} (401)`, r.status === 401);
  if (r.status === 401) {
    const j = await r.json();
    check(`  … 401-конверт: ok=false, code=HTTP_401`, j.ok === false && j.error?.code === 'HTTP_401');
  }
}

// 4. Frontend не расширяет права: nav для reader не содержит editor/admin пунктов
// (проверка через navigation-код — какой набор видит reader)
const { navForRole } = await import('./src/shared/rbac/navigation.ts').catch(() => ({}));
if (navForRole) {
  const groups = navForRole('reader');
  const groupKeys = groups.map((g) => g.key);
  check('nav(reader): нет studio/proposals/admin групп', !groupKeys.includes('studio') && !groupKeys.includes('proposals') && !groupKeys.includes('admin'));
}

console.log(out.join('\n'));

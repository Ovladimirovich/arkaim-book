/** f2-inventory.mjs — F2-аудит: читательское ядро и кандидаты verticals. */
import { readFileSync } from 'node:fs';
const o = JSON.parse(readFileSync('./contracts/openapi.json', 'utf8'));
const m = JSON.parse(readFileSync('./contracts/rbac-matrix.json', 'utf8'));

function schemaName(s) {
  if (!s) return '?';
  if (s.$ref) return s.$ref.split('/').pop();
  if (s.type === 'array') return `array<${schemaName(s.items)}>`;
  return s.type || '?';
}

function show(p) {
  const ops = o.paths[p];
  if (!ops) { console.log(p.padEnd(42), '— НЕ СУЩЕСТВУЕТ'); return; }
  for (const [meth, op] of Object.entries(ops)) {
    if (!['get', 'post', 'put', 'delete', 'patch'].includes(meth)) continue;
    const rbac = m.routes.find((r) => r.path === p && r.methods.includes(meth.toUpperCase()));
    const resp = op.responses?.['200']?.content?.['application/json']?.schema;
    const reqBody = op.requestBody?.content?.['application/json']?.schema;
    console.log(
      p.padEnd(42),
      meth.toUpperCase().padEnd(6),
      'roles:', (rbac ? rbac.roles.join('|') : 'NOT-IN-MATRIX').padEnd(26),
      'req:', schemaName(reqBody).padEnd(28),
      'resp:', schemaName(resp),
    );
  }
}

console.log('=== ЧИТАТЕЛЬСКОЕ ЯДРО (candidates) ===');
for (const p of [
  '/book/ask', '/v1/chat', '/v1/stream',
  '/book/chapters', '/book/text', '/book/genome', '/book/layers',
  '/book', '/book/memory', '/book/knowledge/{topic}',
  '/book/reader/profile', '/book/reader/history', '/book/reader/questions',
  '/book/reader/memory',
]) show(p);

console.log('\n=== WS/SSE (realtime contract) ===');
console.log('POST /v1/stream — SSE, roles?');
const ws = m.routes.find((r) => r.path === '/ws');
console.log('WS /ws — в матрице:', ws ? JSON.stringify(ws) : 'нет (websocket-роут не входит в API-матрицу)');

console.log('\n=== RBAC сравнение candidate-доменов ===');
const domains = {
  'reader-core': ['/book/ask', '/v1/chat', '/v1/stream', '/book/chapters', '/book/text', '/book/genome', '/book/layers', '/book/reader/profile', '/book/reader/history'],
  'community': ['/book/community/interpretations', '/book/community/artifacts', '/book/community/timeline'],
  'temporal(M10.2)': ['/book/temporal/chain', '/book/temporal/pending-updates'],
  'world-explorer': ['/book/world-explorer/explore', '/book/world-explorer/cache/stats'],
};
for (const [d, ps] of Object.entries(domains)) {
  for (const p of ps) {
    const rbac = m.routes.find((r) => r.path === p);
    console.log(d.padEnd(16), p.padEnd(44), rbac ? 'roles: ' + rbac.roles.join('|') : '—');
  }
}

/** f2-schemas.mjs — детальные схемы ключевых F2-контрактов. */
import { readFileSync } from 'node:fs';
const o = JSON.parse(readFileSync('./contracts/openapi.json', 'utf8'));
const S = o.components.schemas;

function typeOf(v) {
  if (v.$ref) return v.$ref.split('/').pop();
  if (v.anyOf) return v.anyOf.map((x) => x.type || (x.$ref ? x.$ref.split('/').pop() : '?')).join(' | ');
  if (v.type === 'array') return `array<${typeOf(v.items)}>`;
  return v.type || '?';
}

for (const n of [
  'BookAskRequest', 'SuccessResponse',
  'ReaderProfileResponse', 'ReaderContextResponse', 'ReaderStatsResponse', 'ReaderTopicItem',
]) {
  const s = S[n];
  if (!s) { console.log('===', n, '— нет ==='); continue; }
  console.log('===', n, '===');
  for (const [k, v] of Object.entries(s.properties || {})) {
    console.log('  ', k.padEnd(24), typeOf(v));
  }
  console.log('   required:', (s.required || []).join(', ') || '—');
}

// /v1/chat и /v1/stream — что за request body (no schema)?
console.log('\n=== /v1/* request body (raw) ===');
for (const p of ['/v1/chat', '/v1/stream']) {
  const post = o.paths[p]?.post;
  console.log(p, '→', JSON.stringify(post?.requestBody || 'no-body').slice(0, 120));
}

// /book/ask responses fully
console.log('\n=== /book/ask operation ===');
const ask = o.paths['/book/ask'].post;
console.log('summary:', ask.summary, '| tags:', (ask.tags || []).join(','));
console.log('resp200:', JSON.stringify(ask.responses['200']).slice(0, 200));

// chapters/text — query params
for (const p of ['/book/chapters', '/book/text', '/book/reader/history']) {
  const op = o.paths[p].get;
  const params = (op.parameters || []).map((x) => x.name + (x.required ? '!' : '')).join(', ');
  console.log('\n===', p, 'GET params:', params || '—', '===');
  console.log('  resp:', JSON.stringify(op.responses['200']).slice(0, 160));
}

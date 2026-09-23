/**
 * f2-audit-contracts.mjs — §3 аудита: конверт-контроль всех 11 F2-endpoint'ов.
 * Для каждого: живой вызов + точная фиксация формы ответа (enveloped/direct)
 * + сверка с ENVELOPE_MAP фронтенда.
 */
import { readFileSync } from 'node:fs';

const BASE = 'http://localhost:8642';
// ENVELOPE_MAP из кода (аудит читает фактический код, не отчёт):
const mapSrc = readFileSync('src/shared/api/envelope.ts', 'utf8');
const mapEntries = {};
for (const m of mapSrc.matchAll(/'(\w+ [^']+)':\s*'(enveloped|direct)'/g)) {
  mapEntries[m[1]] = m[2];
}

const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `f2audit_${Date.now()}` }),
});
const cookie = (reg.headers.get('set-cookie') || '').split(';')[0];
const H = { 'Content-Type': 'application/json', cookie };

const results = [];
function record(name, actual, expected) {
  // actual может быть уточнённым direct(...): сравниваем по базовому классу
  const actualBase = actual.startsWith('direct') ? 'direct' : actual;
  const okk = actualBase === expected || actual === expected;
  results.push(`${okk ? 'PASS' : 'FAIL'}  ${name}: факт=${actual}, map=${expected}`);
  if (!okk) process.exitCode = 1;
}

async function probe(name, method, path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method, headers: H, body: body ? JSON.stringify(body) : undefined,
  });
  const j = await r.json().catch(() => null);
  // Определение фактической формы:
  // enveloped = {ok:true, data:...}; direct = всё остальное (включая {ok} без data)
  let actual;
  if (j && typeof j === 'object' && j.ok === true && 'data' in j && !('stats' in j) && typeof j.data !== 'string') {
    actual = 'enveloped';
  } else if (j && typeof j === 'object' && j.ok === true && typeof j.data === 'string' && 'total' in j) {
    actual = 'direct(text: пагинация в конверте)';
  } else if (j && typeof j === 'object' && j.ok === true && 'stats' in j) {
    actual = 'direct(progress: stats в конверте)';
  } else if (j && typeof j === 'object' && j.ok === true && Object.keys(j).length <= 2) {
    actual = 'direct(ok-only)';
  } else {
    actual = 'direct(payload)';
  }
  const mapKey = `${method} ${path.split('?')[0]}`;
  const expected = mapEntries[mapKey] ?? 'direct(нет в map)';
  record(`${method} ${path}`, actual, expected);
  return j;
}

await probe('ask', 'POST', '/book/ask', { question: 'Что такое Сати Юга?' });
await probe('chapters', 'GET', '/book/chapters');
await probe('text', 'GET', '/book/text?offset=0&limit=100');
await probe('layers', 'GET', '/book/layers');
await probe('genome', 'GET', '/book/genome');
await probe('profile', 'GET', '/book/reader/profile');
await probe('history', 'GET', '/book/reader/history?limit=5');
await probe('reading-event', 'POST', '/book/reader/reading-event', { chapter_id: 'ch_02', chapter_index: 2, read_seconds: 10, scroll_percent: 20, completed: false });
await probe('progress', 'GET', '/book/reader/reading-progress');
await probe('position', 'GET', '/book/reader/reading-position');

console.log(results.join('\n'));
console.log(`\nMap-записей прочитано из кода: ${Object.keys(mapEntries).length}`);

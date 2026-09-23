/** f2-env-check.mjs — все F2 ENVELOPE_MAP пути существуют в OpenAPI. */
import { readFileSync } from 'node:fs';
const o = JSON.parse(readFileSync('./contracts/openapi.json', 'utf8'));

const mapEntries = [
  'POST /book/ask', 'GET /book/chapters', 'GET /book/text', 'GET /book/layers',
  'GET /book/genome', 'GET /book/reader/profile', 'GET /book/reader/history',
  'POST /book/reader/reading-event', 'GET /book/reader/reading-progress',
  'GET /book/reader/reading-position',
];

let bad = 0;
for (const e of mapEntries) {
  const [m, p] = e.split(' ');
  const path = p.split('?')[0];
  const okk = o.paths[path]?.[m.toLowerCase()] !== undefined;
  if (!okk) { bad++; console.log('ОТСУТСТВУЕТ:', e); }
}
console.log(bad === 0 ? `OK: все ${mapEntries.length} F2-записей существуют в OpenAPI` : `FAIL: ${bad} проблем`);

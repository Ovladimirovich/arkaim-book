/**
 * fetch-contract.mjs — снятие слепка OpenAPI с живого backend.
 *
 * Backend — единственный source of truth. Слепок committed в contracts/openapi.json
 * и регенерируется этим скриптом при доступном backend.
 *
 * Источник: GET {BACKEND_URL}/openapi.json (FastAPI, core.main:app).
 */
import { writeFileSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONTRACTS_DIR = resolve(__dirname, '..', 'contracts');
const OUT = resolve(CONTRACTS_DIR, 'openapi.json');

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8642';

async function main() {
  const url = `${BACKEND_URL}/openapi.json`;
  console.log(`[contracts:fetch] GET ${url}`);
  let resp;
  try {
    resp = await fetch(url);
  } catch (e) {
    console.error(`[contracts:fetch] backend недоступен (${e.message}).`);
    if (existsSync(OUT)) {
      console.log('[contracts:fetch] оставляю существующий committed-слепок.');
      process.exit(2); // специальный код: не удалось обновить, слепок есть
    }
    console.error('[contracts:fetch] слепка нет — поднимите backend (port 8642).');
    process.exit(1);
  }
  if (!resp.ok) {
    console.error(`[contracts:fetch] HTTP ${resp.status}`);
    process.exit(1);
  }
  const schema = await resp.json();
  const count = Object.keys(schema.paths || {}).length;
  mkdirSync(CONTRACTS_DIR, { recursive: true });
  const body = JSON.stringify(schema, null, 2) + '\n';
  writeFileSync(OUT, body, 'utf8');
  const prev = existsSync(OUT + '.prev') ? readFileSync(OUT + '.prev', 'utf8') : null;
  console.log(`[contracts:fetch] paths=${count} → ${OUT}${prev && prev !== body ? ' (ИЗМЕНЁН)' : ''}`);
}

main();

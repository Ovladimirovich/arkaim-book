/**
 * contracts.mjs — генерация + верификация typed contracts.
 *
 * Pipeline (F1_SPEC §6):
 *   1. contracts/openapi.json (committed слепок backend) →
 *      openapi-typescript → src/shared/api/generated/schema.d.ts
 *   2. contracts/rbac-matrix.json (committed слепок RBAC) →
 *      генерация src/shared/rbac/generated/matrix.ts
 *   3. verify-режим: регенерация во временную папку и сверка с committed
 *      результатами (CI-гейт: контракты не разошлись).
 *
 * Запуски:
 *   npm run contracts:generate  — регенерация (после обновления слепков)
 *   npm run contracts:verify    — CI-проверка воспроизводимости
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, rmSync, existsSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

const OAPI_JSON = resolve(ROOT, 'contracts', 'openapi.json');
const RBAC_JSON = resolve(ROOT, 'contracts', 'rbac-matrix.json');
const GEN_SCHEMA = resolve(ROOT, 'src/shared/api/generated/schema.d.ts');
const GEN_MATRIX = resolve(ROOT, 'src/shared/rbac/generated/matrix.ts');
const VERIFY = process.argv.includes('--verify');

if (!existsSync(OAPI_JSON)) {
  console.error('[contracts] нет contracts/openapi.json — сначала npm run contracts:fetch');
  process.exit(1);
}
if (!existsSync(RBAC_JSON)) {
  console.error('[contracts] нет contracts/rbac-matrix.json — сначала scripts/dump_rbac_matrix.py');
  process.exit(1);
}

mkdirSync(dirname(GEN_SCHEMA), { recursive: true });
mkdirSync(dirname(GEN_MATRIX), { recursive: true });

// ── 1. OpenAPI → schema.d.ts ────────────────────────────────────
function generateSchema(outPath) {
  // Прямой вызов node-скрипта (не .bin/.cmd — спавн .cmd даёт EINVAL в sandbox)
  const cliJs = resolve(ROOT, 'node_modules/openapi-typescript/bin/cli.js');
  execFileSync(process.execPath, [cliJs, OAPI_JSON, '-o', outPath], {
    stdio: ['ignore', 'ignore', 'inherit'],
  });
}

// ── 2. RBAC json → matrix.ts ─────────────────────────────────────
function renderMatrix() {
  const data = JSON.parse(readFileSync(RBAC_JSON, 'utf8'));
  if (!Array.isArray(data.routes) || data.routes.length === 0) {
    throw new Error('rbac-matrix.json пуст');
  }
  const header = [
    '/**',
    ' * matrix.ts — ГЕНЕРИРОВАНО scripts/contracts.mjs из contracts/rbac-matrix.json.',
    ' * НЕ ПРАВИТЬ РУКАМИ. Источник: фактическая RBAC-матрица backend',
    ` * (живой импорт core.main:app, ${data.total_routes} маршрутов, слепок ${data.generated_at}).`,
    ' */',
    '',
  ].join('\n');

  const lines = [];
  for (const r of data.routes) {
    const methods = r.methods.map((m) => `"${m}"`).join(', ');
    const roles = r.roles.map((x) => `"${x}"`).join(', ');
    lines.push(`  { path: ${JSON.stringify(r.path)}, methods: [${methods}], roles: [${roles}] },`);
  }

  const body = [
    header,
    'export type PathTemplate = string;',
    'export type Method = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";',
    '',
    'export interface RouteRole {',
    '  path: PathTemplate;',
    '  methods: Method[];',
    '  roles: string[];',
    '}',
    '',
    `export const RBAC_MATRIX: RouteRole[] = [`,
    ...lines,
    '];',
    '',
    `export const RBAC_ROUTES_TOTAL = ${data.total_routes};`,
    `export const RBAC_SNAPSHOT_DATE = ${JSON.stringify(data.generated_at)};`,
    '',
  ].join('\n');
  return body;
}

// ── 3. Run ───────────────────────────────────────────────────────
if (VERIFY) {
  // Верификация: генерируем во временное место и сравниваем
  const tmp = resolve(ROOT, '.contracts-tmp');
  rmSync(tmp, { recursive: true, force: true });
  mkdirSync(tmp, { recursive: true });
  const tmpSchema = resolve(tmp, 'schema.d.ts');
  const tmpMatrix = resolve(tmp, 'matrix.ts');

  generateSchema(tmpSchema);
  writeFileSync(tmpMatrix, renderMatrix(), 'utf8');

  let ok = true;
  for (const [tmpF, realF, name] of [
    [tmpSchema, GEN_SCHEMA, 'schema.d.ts'],
    [tmpMatrix, GEN_MATRIX, 'matrix.ts'],
  ]) {
    if (!existsSync(realF)) {
      console.error(`[contracts:verify] ${name} отсутствует — запустите npm run contracts:generate`);
      ok = false;
      continue;
    }
    const a = readFileSync(tmpF, 'utf8');
    const b = readFileSync(realF, 'utf8');
    if (a !== b) {
      console.error(`[contracts:verify] FAIL: ${name} разошёлся с committed-слепком.`);
      ok = false;
    } else {
      console.log(`[contracts:verify] OK: ${name} соответствует слепку.`);
    }
  }
  rmSync(tmp, { recursive: true, force: true });
  process.exit(ok ? 0 : 1);
} else {
  generateSchema(GEN_SCHEMA);
  writeFileSync(GEN_MATRIX, renderMatrix(), 'utf8');
  console.log(`[contracts:generate] schema.d.ts + matrix.ts готовы (${ROOT}/src/shared/*/generated/)`);
}

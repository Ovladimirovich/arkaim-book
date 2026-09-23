/**
 * run-tests.mjs — sandbox-обход: in-process тестовый раннер.
 *
 Проблема среды: sandbox блокирует ВСЕ дочерние spawn (EPERM):
   - vitest CLI (config-loader спавнит node)
   - vitest/node API с config-файлом (то же)
   - node --test (спавнит тест-файлы)
 Проверено: даже legacy-проект vitest в этой сессии не запускается.
 Это ограничение СЕАНСА, не проекта. В CI (actions) всё работает штатно
 (`npx vitest run` — см. ci.yml frontend-v2-test).

 Решение here-and-now: собственный минимальный раннер в ОДНОМ процессе.
 Импортирует тест-модули (TS через встроенный strip-types Node 24),
 '@/'-алиас резолвится через ts-alias-loader.mjs, 'vitest' — через shim.
 НЕ замена vitest; существует для локального прогона в этой сессии.
 */
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

// ── describe/it/expect/vi — общий реестр (используется и vitest-shim) ──
import { describe, it, expect, makeVi, runAll, state, beginModule, endModule, clearTests } from './runner-globals.mjs';

globalThis.describe = describe;
globalThis.it = it;
globalThis.expect = expect;
globalThis.beforeEach = () => {};
globalThis.afterEach = () => {};
globalThis.vi = makeVi();

// jsdom-полифилл минимумов (DOM-тестов в F1-наборе нет, но подключены на всякий)
if (typeof globalThis.document === 'undefined') {
  globalThis.document = { cookie: '' };
}
if (typeof globalThis.window === 'undefined') {
  globalThis.window = { matchMedia: () => ({ matches: false }) };
}
if (typeof globalThis.localStorage === 'undefined') {
  globalThis.localStorage = { getItem: () => null, setItem: () => {} };
}

// ── resolve-хук: '@/x' → '<root>/src/x' + 'vitest' → shim ──
const { register } = await import('node:module');
register(
  new URL('./ts-alias-loader.mjs', import.meta.url),
  pathToFileURL(path.resolve(ROOT, 'package.json')),
);

// ── Тест-файлы ──
// PA-1 (F3 post-audit): явный список — это и есть discovery sandbox-раннера
// (CI-vitest находит файлы сам по default-glob tests/**; здесь spawn EPERM).
// F3-файлы регистрировались с пропуском — 67/67 не включало их. Добавлены.
const TESTS = [
  'tests/unit/errors.test.ts',
  'tests/unit/rbac.test.ts',
  'tests/unit/auth.test.ts',
  'tests/unit/ws-client.test.ts',
  'tests/unit/sse.test.ts',
  'tests/unit/contracts.test.ts',
  'tests/unit/login-b2.test.ts',
  'tests/unit/book.test.ts',
  'tests/unit/reader.test.ts',
  'tests/unit/source-badge.test.ts',
  'tests/unit/temporal.test.ts',
  'tests/unit/provenance-badge.test.ts',
  'tests/unit/reading/reading-types.test.ts',
  'tests/unit/reading/reading-navigation-pure.test.ts',
  'tests/unit/reading/reading-auto-load-logic.test.ts',
  'tests/unit/reading/reading-context-transfer.test.ts',
  'tests/unit/reading/use-reading-settings-logic.test.ts',
];

for (const t of TESTS) {
  const url = pathToFileURL(path.resolve(ROOT, t)).href;
  console.log(`\nRUN ${t}`);
  // Per-module изоляция (как vitest isolate): свежий vi + прогон + очистка
  // ДО следующего модуля — иначе stubGlobal/restoreAllMocks разных файлов
  // конфликтуют (fetch-моки и глобалы пересекались в F2-наборе).
  globalThis.vi = makeVi();
  beginModule();
  try {
    await import(url);
    await runAll();
  } catch (e) {
    state.failed++;
    state.failures.push({ name: t, error: e });
    console.error(`  ✗ MODULE LOAD: ${e.message}`);
  } finally {
    clearTests();
    endModule();
  }
}

// ── Исполнение тестов — теперь per-module (внутри цикла выше) ──

console.log(`\n${'='.repeat(60)}`);
console.log(`PASSED: ${state.passed}  FAILED: ${state.failed}`);
for (const f of state.failures) console.log(`  FAILED: ${f.name}: ${f.error?.message}`);
process.exit(state.failed > 0 ? 1 : 0);

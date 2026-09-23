/**
 * f2-e2e-http.mjs — HTTP-уровень E2E (sandbox-компенсация).
 * Браузерный playwright-прогон в этой среде невозможен: spawn EPERM на
 * chrome.exe (то же средовое ограничение, что и vitest CLI — см. run-tests.mjs).
 *
 * Экраны F2 — client-компоненты (App.useApp и т.п.): их доменный контент
 * появляется в браузере, а не в статике пререндера. Поэтому HTTP-слой
 * проверяет: маршруты отвечают, это корректные Next-страницы приложения v2
 * (не 404/500), в статике есть hydration-данные страницы.
 * Полный интерактивный flow покрыт f2-live-smoke.mjs (12 контрактов),
 * браузерный прогон — tests/e2e/foundation.spec.ts (CI/локально).
 */
const BASE = process.env.E2E_BASE_URL || 'http://localhost:3001';
const results = [];
function check(name, cond, extra = '') {
  results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) process.exitCode = 1;
}

const F2_ROUTES = ['/', '/login', '/register', '/reading', '/profile', '/status', '/no-access'];

for (const path of F2_ROUTES) {
  const r = await fetch(`${BASE}${path}`);
  const html = await r.text();
  const isNextApp =
    r.status === 200 &&
    html.includes('<!DOCTYPE html>') &&
    (html.includes('__next_f') || html.includes('_next/static'));
  // Страница-не-404: next отдаёт кастомный _not-found только для неизвестных маршрутов
  const notFound = html.includes('404') && html.includes('This page could not be found');
  check(`${path} → 200, Next-страница v2`, isNextApp && !notFound);
}

// Известный несуществующий маршрут → честный 404 (не молчание)
const nf = await fetch(`${BASE}/definitely-not-a-page`);
check('unknown route → 404/307 (не 200-заглушка)', nf.status === 404 || nf.status === 307 || nf.status === 308);

console.log(results.join('\n'));
const fails = results.filter((r) => r.startsWith('FAIL')).length;
console.log(`\nF2 HTTP-E2E: ${results.length - fails}/${results.length} PASS`);
if (fails > 0) process.exit(1);

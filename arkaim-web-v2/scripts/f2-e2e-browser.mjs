/**
 * f2-e2e-browser.mjs — браузерный E2E без playwright test-runner (sandbox-обход).
 * Раннер playwright спавнит worker'ов (EPERM в этой среде) — поэтому те же
 * сценарии исполняются через library API в ОДНОМ процессе (как run-tests.mjs).
 * Сценарии = tests/e2e/foundation.spec.ts (F2_SPEC §12).
 */
import { chromium } from '@playwright/test';
import { existsSync } from 'node:fs';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:3001';
const results = [];
function pass(name) { results.push(`PASS  ${name}`); }
function fail(name, err) { results.push(`FAIL  ${name} — ${err}`); process.exitCode = 1; }

// Sandbox: playwright 1.61 ждёт chromium_headless_shell-1243, а установлены
// ревизии 1208/1228/1234 — используем существующий chromium-1234 напрямую.
const CHROME = 'C:/Users/1/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe';
const launchOpts = existsSync(CHROME) ? { executablePath: CHROME } : {};

async function main() {
  const browser = await chromium.launch(launchOpts);
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  // 1. login offers register
  try {
    await page.goto(`${BASE}/login`);
    const t = await page.textContent('body');
    if (t.includes('Вход в «Наследие Аркаима»') && t.includes('Зарегистрироваться')) pass('1. login: форма входа');
    else fail('1. login: форма входа', 'нет текста');
  } catch (e) { fail('1. login: форма входа', e.message); }

  // 2. register lands on Ask screen
  try {
    await page.goto(`${BASE}/register`);
    await page.getByLabel('Имя пользователя').fill(`e2e_${Date.now()}`);
    await page.getByRole('button', { name: 'Создать аккаунт' }).click();
    await page.waitForSelector('text=Спросить книгу', { timeout: 30000 });
    pass('2. register → домашний экран «Спросить книгу»');
  } catch (e) { fail('2. register → Ask', e.message); }

  // 3. unauth root → /login redirect
  try {
    await ctx.clearCookies();
    await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
    await page.waitForURL(/\/login/, { timeout: 20000 });
    pass('3. unauth / → redirect /login');
  } catch (e) { fail('3. unauth redirect', e.message); }

  // 4. ask → ответ с бейджем источника; профиль показывает тему
  try {
    await page.goto(`${BASE}/register`);
    await page.getByLabel('Имя пользователя').fill(`e2e_ask_${Date.now()}`);
    await page.getByRole('button', { name: 'Создать аккаунт' }).click();
    await page.waitForSelector('text=Спросить книгу', { timeout: 30000 });

    await page.getByPlaceholder(/Например:/).fill('Что такое Кали Юга?');
    await page.getByRole('button', { name: 'Спросить', exact: true }).click();
    await page.waitForSelector('text=Ответ книги', { timeout: 60000 });
    const badge = await page.locator('.ant-tag').first().textContent();
    if (badge && badge.length > 0) pass(`4a. ask → ответ книги, бейдж «${badge.trim()}»`);
    else fail('4a. ask-бейдж', 'бейдж пуст');

    await page.goto(`${BASE}/profile`);
    await page.waitForSelector('text=Вопросов книге', { timeout: 20000 });
    const body = await page.textContent('body');
    if (body.includes('Темы (память книги о вас)')) pass('4b. profile: темы памяти книги');
    else fail('4b. profile темы', 'нет блока тем');
  } catch (e) { fail('4. ask+profile', e.message); }

  // 5. reading: список глав + открытие главы
  try {
    await page.goto(`${BASE}/reading`);
    await page.waitForSelector('text=Чтение', { timeout: 20000 });
    await page.getByRole('button', { name: 'читать' }).first().click();
    await page.waitForSelector('text=← К оглавлению', { timeout: 20000 });
    const body = await page.textContent('body');
    if (body.includes('Загружено')) pass('5. reading: глава открыта, текст загружен');
    else fail('5. reading', 'нет индикатора загрузки текста');
  } catch (e) { fail('5. reading', e.message); }

  // 6. status dashboard (F1-регресс)
  try {
    await page.goto(`${BASE}/status`);
    await page.waitForSelector('text=Статус системы', { timeout: 20000 });
    pass('6. /status: F1-дашборд доступен (регресс)');
  } catch (e) { fail('6. /status', e.message); }

  await browser.close();
}

main()
  .catch((e) => {
    fail('браузер', e.message);
  })
  .finally(() => {
    console.log(results.join('\n'));
    const fails = results.filter((r) => r.startsWith('FAIL')).length;
    console.log(`\nF2 browser E2E: ${results.length - fails}/${results.length} PASS`);
  });

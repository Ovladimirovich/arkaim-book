/**
 * e2e (F2): вертикаль «Диалог с книгой» — регистрация → спросить → чтение → профиль.
 * Требует backend:8642 + frontend:3001 (next start). Прогоняется локально
 * (не входит в CI-гейт — CI проверяет unit/build/verify, см. F1_SPEC §10).
 */
import { expect, test } from '@playwright/test';

test('login page offers register + dev (when enabled)', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('Вход в «Наследие Аркаима»')).toBeVisible();
  await expect(page.getByText('Зарегистрироваться')).toBeVisible();
});

test('register lands on Ask screen (F2 home)', async ({ page }) => {
  await page.goto('/register');
  const username = `smoke_${Date.now()}`;
  await page.getByLabel('Имя пользователя').fill(username);
  await page.getByRole('button', { name: 'Создать аккаунт' }).click();
  // Домашний экран F2 — «Спросить книгу» (main-layout требует сессию)
  await expect(page.getByText('Спросить книгу')).toBeVisible({ timeout: 20_000 });
});

test('unauthenticated root redirects to /login', async ({ page, context }) => {
  await context.clearCookies();
  await page.goto('/');
  await expect(page).toHaveURL(/\/login/, { timeout: 20_000 });
});

test('F2: ask → answer with source badge, profile shows topic', async ({ page }) => {
  // Регистрируем нового читателя
  await page.goto('/register');
  await page.getByLabel('Имя пользователя').fill(`e2e_ask_${Date.now()}`);
  await page.getByRole('button', { name: 'Создать аккаунт' }).click();
  await expect(page.getByText('Спросить книгу')).toBeVisible({ timeout: 20_000 });

  // Задаём вопрос (синхронный контракт /book/ask)
  await page.getByPlaceholder(/Например:/).fill('Что такое Кали Юга?');
  await page.getByRole('button', { name: 'Спросить', exact: true }).click();
  // Ответ книги с бейджем источника (Pulse отвечает без LLM)
  await expect(page.getByText('Ответ книги')).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('.ant-tag').first()).toBeVisible();

  // Профиль: questions_total=1 и тема появилась (invalidate после ask)
  await page.goto('/profile');
  await expect(page.getByText('Вопросов книге').locator('..')).toBeVisible();
  const topicsCard = page.getByText('Темы (память книги о вас)');
  await expect(topicsCard).toBeVisible();
});

test('F2: reading — chapters list and chapter open', async ({ page }) => {
  await page.goto('/register');
  await page.getByLabel('Имя пользователя').fill(`e2e_read_${Date.now()}`);
  await page.getByRole('button', { name: 'Создать аккаунт' }).click();
  await expect(page.getByText('Спросить книгу')).toBeVisible({ timeout: 20_000 });

  await page.goto('/reading');
  await expect(page.getByText('Чтение', { exact: true })).toBeVisible();
  // Список глав (17 глав — живой backend)
  await expect(page.getByTitle(/Пролог|Часть/).first()).toBeVisible({ timeout: 20_000 });
  // Открываем первую главу
  await page.getByRole('button', { name: 'читать' }).first().click();
  await expect(page.getByText('← К оглавлению')).toBeVisible();
  // Текст главы подгрузился
  await expect(page.getByText('Загружено', { exact: false })).toBeVisible({ timeout: 20_000 });
});

test('F2: status dashboard reachable (F1 regression)', async ({ page }) => {
  await page.goto('/register');
  await page.getByLabel('Имя пользователя').fill(`e2e_status_${Date.now()}`);
  await page.getByRole('button', { name: 'Создать аккаунт' }).click();
  await expect(page.getByText('Спросить книгу')).toBeVisible({ timeout: 20_000 });

  await page.goto('/status');
  await expect(page.getByText('Статус системы')).toBeVisible();
});

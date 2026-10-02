import { expect, test } from '@playwright/test';

const routes = [
  { path: '/ask', ready: 'Задайте вопрос книге' },
  { path: '/history', ready: 'История вопросов' },
  { path: '/world-engine', ready: 'World Engine' },
] as const;

test('B10 smoke: основные data-heavy маршруты открываются без новых console errors', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  for (const route of routes) {
    await page.goto(route.path, { waitUntil: 'networkidle' });
    await expect(page.getByText(route.ready, { exact: true }).first()).toBeVisible();
  }

  expect(consoleErrors).toEqual([]);
});
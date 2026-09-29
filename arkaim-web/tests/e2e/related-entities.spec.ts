import { test, expect } from '@playwright/test';

/**
 * Regression: the question contains a name inside a sentence. The old World
 * Engine substring search treated the entire question as one query and then
 * returned unrelated fallback entities. The deterministic resolver must keep
 * the explicitly mentioned character.
 */
test('Кто такой Велик? shows a relevant World Engine card', async ({ page }) => {
  const pageErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await page.goto('/ask');
  await expect(page.getByText('Кто такой Велик?', { exact: true })).toBeVisible();

  await page.getByText('Кто такой Велик?', { exact: true }).first().click();

  // Stream answer + metadata card are delivered only after the backend closes
  // the SSE response. Wait for the interactive card instead of a fixed delay.
  const velikCard = page.locator('div').filter({
    has: page.getByRole('button', { name: /Открыть в World/ }),
    hasText: /^Велик/,
  }).last();
  await expect(velikCard).toBeVisible({ timeout: 30_000 });
  await expect(velikCard.getByRole('button', { name: /Открыть в World/ })).toBeVisible();
  expect(pageErrors).toEqual([]);
});
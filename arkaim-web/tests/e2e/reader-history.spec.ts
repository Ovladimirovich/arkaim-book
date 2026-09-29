import { expect, test } from '@playwright/test';

function waitForHistory(page: import('@playwright/test').Page) {
  return page.waitForResponse((response) =>
    response.url().includes('/book/reader/history?') && response.status() === 200
  );
}

function firstContentLocator(page: import('@playwright/test').Page, content: string) {
  return page.getByText(content, { exact: true }).first();
}

test.describe('Reader history — Этап 5', () => {
  test.beforeEach(async ({ context }) => {
    const response = await context.request.post('/api/auth/dev-login');
    expect(response.ok()).toBeTruthy();
  });

  test('отображает реальные вопросы и статистику', async ({ context, page }) => {
    const historyResponsePromise = waitForHistory(page);
    await page.goto('/history');

    const historyPayload = await (await historyResponsePromise).json();

    expect(historyPayload.ok).toBe(true);
    expect(historyPayload.data.length).toBeGreaterThan(0);
    expect(historyPayload.data[0]).toEqual(expect.objectContaining({
      session_id: expect.any(String),
      content: expect.any(String),
      created_at: expect.any(String),
    }));

    const expectedContent = historyPayload.data[0].content;
    expect(expectedContent.trim()).not.toBe('');

    const content = firstContentLocator(page, expectedContent);
    await expect(content).toBeVisible();
    await expect(content).toHaveCSS('color', /^rgb\(/);

    const statsResponse = await context.request.get('/book/reader/history/stats');
    expect(statsResponse.ok()).toBeTruthy();

    const statsPayload = await statsResponse.json();
    expect(statsPayload.questions).toBeGreaterThan(0);
    expect(statsPayload.sessions).toBeGreaterThan(0);

    const questionsValue = page.locator('div:has(> div:text-is("Вопросов")) > div:nth-child(2)');
    const sessionsValue = page.locator('div:has(> div:text-is("Сессий")) > div:nth-child(2)');

    await expect(questionsValue).toHaveText(String(statsPayload.questions));
    await expect(questionsValue).toHaveCSS('color', /^rgb\(/);

    await expect(sessionsValue).toHaveText(String(statsPayload.sessions));
    await expect(sessionsValue).toHaveCSS('color', /^rgb\(/);
  });

  test('данные сохраняются после F5', async ({ page }) => {
    const initialResponsePromise = waitForHistory(page);
    await page.goto('/history');
    const initialPayload = await (await initialResponsePromise).json();
    const expectedContent = initialPayload.data[0].content;
    expect(expectedContent.trim()).not.toBe('');

    await expect(firstContentLocator(page, expectedContent)).toBeVisible();

    const reloadResponsePromise = waitForHistory(page);
    await page.reload({ waitUntil: 'networkidle' });
    const reloadPayload = await (await reloadResponsePromise).json();

    expect(reloadPayload.data.map((item: { content: string }) => item.content)).toContain(expectedContent);
    await expect(firstContentLocator(page, expectedContent)).toBeVisible();
  });

  test('фильтр выбирает сессию и показывает диалог', async ({ context, page }) => {
    const sessionsResponse = await context.request.get('/book/reader/history/sessions');
    expect(sessionsResponse.ok()).toBeTruthy();

    const sessionsPayload = await sessionsResponse.json();
    expect(sessionsPayload.data.length).toBeGreaterThan(0);

    await page.goto('/history');
    const sessionSelect = page.locator('select');
    await expect(sessionSelect).toBeVisible();
    await expect(sessionSelect).toHaveCSS('color', /^rgb\(/);
    await sessionSelect.selectOption(sessionsPayload.data[0].session_id);

    await expect(page.getByText('Вы', { exact: true }).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Книга', { exact: true }).first()).toBeVisible();
  });
});
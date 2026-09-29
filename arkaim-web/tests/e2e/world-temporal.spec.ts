import { expect, test } from '@playwright/test';

type TemporalNode = {
  id: string;
  label: string;
  era_id: string;
  entity_ids: string[];
};

type ChainPayload = {
  ok: boolean;
  data: {
    nodes: TemporalNode[];
  };
};

test.describe('Сквозная навигация World → Temporal', () => {
  test.beforeEach(async ({ context }) => {
    const response = await context.request.post('/api/auth/dev-login');
    expect(response.ok()).toBeTruthy();
  });

  test('/world-engine открывает сущность и ведет в /temporal', async ({ page }) => {
    const entityId = 'region_arkaim';
    const contextResponsePromise = page.waitForResponse((response) =>
      response.url().includes(`/book/world/entity/${entityId}/context`) && response.status() === 200
    );

    await page.goto(`/world-engine?entity_id=${encodeURIComponent(entityId)}`);
    await contextResponsePromise;

    await expect(page.getByRole('heading', { name: 'World Engine' })).toBeVisible();
    await expect(page.getByText(`ID: ${entityId}`)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Контекст сущности')).toBeVisible();

    await page.getByRole('button', { name: 'Временной контекст' }).click();
    await expect(page).toHaveURL(new RegExp(`/temporal\\?entity=${entityId}`));
    await expect(page.getByRole('heading', { name: 'Временной контекст' })).toBeVisible({ timeout: 15_000 });
  });

  test('/temporal использует реальную цепочку и возвращает в World', async ({ context, page }) => {
    const chainResponse = await context.request.get('/book/temporal/chain');
    expect(chainResponse.ok()).toBeTruthy();

    const chainPayload = (await chainResponse.json()) as ChainPayload;
    expect(chainPayload.ok).toBe(true);
    expect(chainPayload.data.nodes.length).toBeGreaterThan(0);

    const entityId = 'region_arkaim';
    const linkedNodes = chainPayload.data.nodes.filter((node) => node.entity_ids.includes(entityId));
    const visibleNodes = linkedNodes.length > 0 ? linkedNodes : chainPayload.data.nodes;
    const firstNode = visibleNodes[0];

    const temporalResponsePromise = page.waitForResponse((response) =>
      response.url().includes('/book/temporal/chain') && response.status() === 200
    );
    await page.goto(`/temporal?entity=${encodeURIComponent(entityId)}`);
    await temporalResponsePromise;

    await expect(page.getByRole('heading', { name: 'Временной контекст' })).toBeVisible();
    await expect(page.getByText(`Сущность: ${entityId}`)).toBeVisible();
    await expect(
      page.getByText(linkedNodes.length > 0 ? 'Связанные эпохи' : 'Временная цепочка книги'),
    ).toBeVisible();
    await expect(page.getByText(firstNode.label, { exact: true })).toBeVisible();

    const contextResponsePromise = page.waitForResponse((response) =>
      response.url().includes(`/book/temporal/context/${firstNode.era_id}`) && response.status() === 200
    );
    const epochButton = page.getByRole('button').filter({ hasText: firstNode.label }).first();
    await epochButton.click();
    await contextResponsePromise;

    await expect(page.getByText('Событий:')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Персонажей:')).toBeVisible();
    await expect(page.getByText('Технологий:')).toBeVisible();

    await page.getByRole('button', { name: 'Открыть в World' }).click();
    await expect(page).toHaveURL(new RegExp(`/world-engine\\?entity_id=${entityId}`));
    await expect(page.getByText(`ID: ${entityId}`)).toBeVisible({ timeout: 15_000 });
  });
});
/**
 * tests/e2e/reading-flow.spec.ts — E2E testing для Reading UX redesign.
 *
 * Сценарии:
 * S1: Reading start → TOC visible
 * S2: Continue reading → auto-redirect to last chapter
 * S3: Navigate chapters → prev/next work
 * S4: Context actions → "Спросить о главе" redirects with context
 * S5: Mobile layout → TOC overlay
 * S6: Settings panel → opens and closes
 */
import { test, expect } from '@playwright/test';

test.describe('Reading UX Flow', () => {
  test('S1: Reading page shows TOC list on initial load', async ({ page }) => {
    // Navigate to reading page
    await page.goto('/reading');
    
    // Should see chapter titles (not "Чтение" header from old UI)
    await expect(page.locator('h1')).toContainText(/Наследие Аркаима/i);
    
    // Should see chapter list items
    const chapterItems = page.locator('button').filter({ hasText: /Глава/i });
    await expect(chapterItems.first()).toBeVisible();
  });

  test('S2: Continue reading loads last chapter', async ({ page }) => {
    await page.goto('/reading?continue=1');
    
    // Should be in reading mode, not TOC list
    // Check for reading topbar
    const topbar = page.locator('header').first();
    await expect(topbar).toBeVisible();
  });

  test('S3: Chapter navigation buttons exist', async ({ page }) => {
    await page.goto('/reading');
    
    // Click on a chapter to enter reading mode
    const firstChapter = page.locator('button').filter({ hasText: /Глава/i }).first();
    await firstChapter.click();
    
    // Should see prev/next buttons in bottom nav
    const prevBtn = page.getByRole('button', { name: /пред/i });
    const nextBtn = page.getByRole('button', { name: /след/i });
    
    await expect(prevBtn).toBeVisible();
    await expect(nextBtn).toBeVisible();
  });

  test('S4: "Ask about chapter" action preserves context', async ({ page }) => {
    await page.goto('/reading');
    
    // Enter reading mode
    const firstChapter = page.locator('button').filter({ hasText: /Глава/i }).first();
    await firstChapter.click();
    
    // Click the "Ask" button in topbar
    const askBtn = page.getByRole('button', { name: /спросить/i }).first();
    await askBtn.click();
    
    // Should redirect to / with ask param
    await expect(page.url()).toContain('/?ask=');
  });

  test('S5: Mobile layout — TOC overlay', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/reading');
    
    // Should see hamburger/menu button
    const menuBtn = page.getByRole('button', { name: /оглавление/i });
    await expect(menuBtn).toBeVisible();
    
    // Click menu to open TOC overlay
    await menuBtn.click();
    
    // TOC should be visible as overlay (full screen)
    const tocItems = page.locator('nav[aria-label="Оглавление"] button');
    await expect(tocItems.first()).toBeVisible();
  });

  test('S6: Settings panel opens and has typography controls', async ({ page }) => {
    await page.goto('/reading');
    
    // Enter reading mode
    const firstChapter = page.locator('button').filter({ hasText: /Глава/i }).first();
    await firstChapter.click();
    
    // Click settings button
    const settingsBtn = page.getByRole('button', { name: /настройки/i });
    await settingsBtn.click();
    
    // Settings modal should appear
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();
    
    // Should have font size options
    const fontSizeBtn = page.getByRole('button', { name: /16px/i });
    await expect(fontSizeBtn).toBeVisible();
    
    // Close settings
    const closeBtn = modal.getByRole('button', { name: /закрыть/i });
    await closeBtn.click();
    await expect(modal).not.toBeVisible();
  });

  test('S7: Progress bar shows at bottom of reading view', async ({ page }) => {
    await page.goto('/reading');
    
    // Enter reading mode
    const firstChapter = page.locator('button').filter({ hasText: /Глава/i }).first();
    await firstChapter.click();
    
    // Should see progress info at bottom
    const progressText = page.getByText(/прогресс/i);
    await expect(progressText).toBeVisible();
  });

  test('S8: Reading typography uses serif font', async ({ page }) => {
    await page.goto('/reading');
    
    // Enter reading mode
    const firstChapter = page.locator('button').filter({ hasText: /Глава/i }).first();
    await firstChapter.click();
    
    // Chapter title should use serif font
    const chapterTitle = page.locator('h1');
    await expect(chapterTitle).toBeVisible();
    const fontFamily = await chapterTitle.evaluate(el => 
      window.getComputedStyle(el).fontFamily
    );
    expect(fontFamily).toContain('Georgia');
  });

  test('S9: Back to TOC from reading view', async ({ page }) => {
    await page.goto('/reading');
    
    // Enter reading mode
    const firstChapter = page.locator('button').filter({ hasText: /Глава/i }).first();
    await firstChapter.click();
    
    // Find and click "Back to TOC" or similar
    const backBtn = page.getByRole('button', { name: /оглавление/i }).last();
    await backBtn.click();
    
    // Should be back at chapter list
    await expect(page.locator('h1')).toContainText(/Наследие Аркаима/i);
  });

  test('S10: Reading page is full height, no AppShell sidebar', async ({ page }) => {
    await page.goto('/reading');
    
    // Should NOT have the sidebar from AppShell
    const sidebar = page.locator('[class*="ant-layout-sider"]');
    await expect(sidebar).not.toBeVisible();
    
    // Should have reading-specific layout
    const readingContainer = page.locator('[data-reading-theme]');
    await expect(readingContainer).toBeVisible();
  });
});

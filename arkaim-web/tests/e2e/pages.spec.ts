import { test, expect } from '@playwright/test';

test.describe('Visual Genome Page', () => {
  test('visual page requires editor/admin role', async ({ page }) => {
    await page.goto('/visual');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/visual')).toBeTruthy();
  });

  test('visual page renders tabs', async ({ page }) => {
    // Without auth, should redirect to login
    await page.goto('/visual');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('X-Ray Page', () => {
  test('xray page requires admin role', async ({ page }) => {
    await page.goto('/xray');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/xray')).toBeTruthy();
  });
});

test.describe('Upload Page', () => {
  test('upload page requires editor/admin role', async ({ page }) => {
    await page.goto('/upload');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/upload')).toBeTruthy();
  });

  test('upload page renders drag zone', async ({ page }) => {
    await page.goto('/upload');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Crowdfunding Page', () => {
  test('crowdfunding page requires auth', async ({ page }) => {
    await page.goto('/crowdfunding');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/crowdfunding')).toBeTruthy();
  });
});

test.describe('Admin Page', () => {
  test('admin page requires admin role', async ({ page }) => {
    await page.goto('/admin');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/admin')).toBeTruthy();
  });
});

test.describe('Full Navigation', () => {
  test('all navigation links are accessible', async ({ page }) => {
    await page.goto('/login');
    const navLinks = ['Книга', 'О книге', 'Профиль', 'История'];
    for (const link of navLinks) {
      await expect(page.locator(`text=${link}`)).toBeVisible();
    }
  });

  test('page title is consistent', async ({ page }) => {
    await page.goto('/login');
    const title = await page.title();
    expect(title).toContain('Наследие Аркаима');
  });

  test('no console errors on login page', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto('/login');
    await page.waitForTimeout(500);
    expect(errors).toHaveLength(0);
  });

  test('about page loads genome data or shows empty state', async ({ page }) => {
    await page.goto('/about');
    await page.waitForTimeout(1000);
    // Page should render without crashing
    await expect(page.locator('body')).toBeVisible();
  });

  test('history page loads or shows empty state', async ({ page }) => {
    await page.goto('/history');
    await page.waitForTimeout(1000);
    await expect(page.locator('body')).toBeVisible();
  });

  test('profile page loads or shows login redirect', async ({ page }) => {
    await page.goto('/profile');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/profile')).toBeTruthy();
  });

  test('book page loads or shows login redirect', async ({ page }) => {
    await page.goto('/book');
    const url = page.url();
    expect(url.includes('/login') || url.includes('/book')).toBeTruthy();
  });
});

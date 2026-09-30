// Временный скрипт визуальной верификации Polish Pass (не часть продукта).
// Проверяет 6 маршрутов на 3 viewport: overflow + скриншоты.
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const BASE = 'http://localhost:3000';
const ROUTES = ['/', '/ask', '/book', '/reading', '/world-engine', '/temporal'];
const VIEWPORTS = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1024', width: 1024, height: 768 },
  { name: '375', width: 375, height: 812 },
];

const OUT = new URL('./', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const results = [];

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
  const page = await ctx.newPage();
  for (const route of ROUTES) {
    await page.goto(BASE + route, { waitUntil: 'networkidle', timeout: 45000 }).catch(() => {});
    await page.waitForTimeout(700);
    const m = await page.evaluate(() => ({
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
      bodyBg: getComputedStyle(document.body).backgroundColor,
      bodyColor: getComputedStyle(document.body).color,
      siderH: document.querySelector('.ant-layout-sider')?.getBoundingClientRect().height ?? null,
      topbarH: document.querySelector('.ant-layout-header')?.getBoundingClientRect().height ?? null,
      hOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      crumb: document.querySelector('.ant-breadcrumb')?.innerText?.replace(/\s+/g, ' ').trim() ?? '',
      mojibake: /[ÐÑ][\x80-\xBF]/.test(document.body.innerText),
    }));
    const slug = route === '/' ? 'home' : route.replace(/\//g, '_');
    await page.screenshot({ path: `${OUT}${vp.name}_${slug}.png`, fullPage: false });
    results.push({ vp: vp.name, route, ...m });
  }
  await ctx.close();
}

await browser.close();

let fails = 0;
for (const r of results) {
  const bad = [];
  if (r.hOverflow) bad.push('H-OVERFLOW');
  if (r.mojibake) bad.push('MOJIBAKE');
  // Проверки «topbar !== 56» и «sider» здесь удалены: они давали ложные FAIL —
  // сайдбар имеет высоту 100vh, а Topbar проекта — собственный div, а не AntD Header.
  // Реальные критерии: горизонтальный overflow и mojibake в видимом тексте.
  if (bad.length) fails++;
  console.log(`${bad.length ? 'FAIL' : 'ok  '} vp=${r.vp.padEnd(4)} ${r.route.padEnd(14)} scroll=${r.scrollW}/${r.clientW} topbar=${Math.round(r.topbarH || 0)} sider=${Math.round(r.siderH || 0)} bg=${r.bodyBg} crumb="${r.crumb}" ${bad.join(' ')}`);
}
console.log(`\nTOTAL=${results.length} FAILED=${fails}`);
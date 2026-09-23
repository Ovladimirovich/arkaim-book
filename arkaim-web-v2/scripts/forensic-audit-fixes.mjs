/** forensic-audit-fixes.mjs — уточнение двух проверок: REG.1 (auth) и MEDIA.1 (только temporal-пути). */
const BASE = 'http://localhost:8642';

// REG.1: /pending-updates с реальным reader → должен быть 200 (reader+ разрешён)
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: `forensic-ta-${Date.now()}@audit.local`, password: 'AuditPass123', display_name: 'Forensic TA' }),
});
const setCookie = reg.headers.get('set-cookie') ?? '';
const cookie = setCookie.split(';')[0];
const regBody = await reg.json();
console.log('register:', reg.status, regBody?.user?.role ?? regBody?.error?.code);

const pend = await fetch(`${BASE}/book/temporal/pending-updates`, { headers: { Cookie: cookie } });
const pendBody = await pend.json();
console.log(`REG.1(исправл.): /pending-updates с reader = ${pend.status} → ${pend.status === 200 ? 'PASS (жив, reader разрешён)' : 'FAIL'}`, JSON.stringify(pendBody).slice(0, 120));

// MEDIA.1: только temporal-пути
const oa = await (await fetch(`${BASE}/openapi.json`)).json();
const temporalPaths = Object.keys(oa.paths).filter((p) => p.includes('/temporal'));
const temporalOnly = JSON.stringify(Object.fromEntries(Object.entries(oa.paths).filter(([k]) => temporalPaths.includes(k))));
const mediaWords = ['comfy', 'workflow', 'image', 'video', 'audio', 'prompt_builder', 'sdxl', 'checkpoint', 'model_ref', 'generation', 'render', 'texture', 'mesh', 'lod'];
const found = mediaWords.filter((w) => temporalOnly.toLowerCase().includes(w));
console.log(`MEDIA.1(исправл.): media-backend слова ТОЛЬКО в temporal-путях: ${found.length === 0 ? 'PASS (0 найдено)' : 'FAIL: ' + found.join(',')}`, '| проверено путей:', temporalPaths.length);

// Дополнительно: temporal-модели запросов (components/schemas), использованные temporal-путями
const temporalSchemasUsed = new Set();
for (const p of temporalPaths) {
  const ops = oa.paths[p];
  for (const method of Object.values(ops ?? {})) {
    const refs = JSON.stringify(method);
    for (const m of refs.matchAll(/#\/components\/schemas\/(\w+)/g)) temporalSchemasUsed.add(m[1]);
  }
}
const schemaJson = JSON.stringify(Object.fromEntries([...temporalSchemasUsed].map((s) => [s, oa.components?.schemas?.[s] ?? null])));
const foundS = mediaWords.filter((w) => schemaJson.toLowerCase().includes(w));
console.log(`MEDIA.1b: media-backend слова в temporal-СХЕМАХ (${[...temporalSchemasUsed].join(', ')}): ${foundS.length === 0 ? 'PASS (0 найдено)' : 'FAIL: ' + foundS.join(',')}`);

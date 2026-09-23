/**
 * f3-followup-live.mjs — live-проверки F3 FOLLOW-UP (критический повтор).
 *
 * Node-скрипт. Backend уже запущен на :8642 (фоновая задача).
 */
const BASE = 'http://127.0.0.1:8642';

async function req(method, path, body, cookie) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (cookie) headers['Cookie'] = cookie;
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  let json = null;
  try { json = await res.json(); } catch {}
  const setCookie = res.headers.get('set-cookie');
  return { status: res.status, json, setCookie };
}

// ── Чтение словарей provenance (FE-компонент vs BE-первоисточник) ──
const { readFileSync } = await import('node:fs');

function parseBeDict() {
  const src = readFileSync('../core/CORE/narrative_engine/source_levels.py', 'utf8');
  const dict = src.slice(src.indexOf('SOURCE_CATEGORY_LABELS'), src.indexOf('class ProvenanceTag'));
  const out = {};
  const re = /ProvenanceCategory\.([A-Z_]+):\s*\{\s*"label":\s*"([^"]+)",\s*"color":\s*"([^"]+)"/g;
  let m;
  while ((m = re.exec(dict)) !== null) out[m[1]] = { label: m[2], color: m[3] };
  return out;
}

function parseFeDict() {
  return readFileSync('src/shared/ui/ProvenanceBadge.tsx', 'utf8');
}

const results = [];

// 1. temporal chain — today вне отношений, Modernity->Arkaim отсутствует
{
  const { status, json } = await req('GET', '/book/temporal/chain');
  const chain = json.data;
  const rels = chain.relations;
  // temporal_today — точка наблюдателя: в /nodes (13), но НЕ в цепочке /chain (12 эпох).
  const today = chain.nodes.find((n) => n.id === 'temporal_today');
  results.push(['chain 200 enveloped', status === 200 && json.ok === true]);
  results.push(['chain nodes = 12 эпох (today НЕ в цепочке)', chain.nodes.length === 12]);
  results.push(['today NOT in chain nodes', today === undefined]);
  const todayInRels = rels.some(
    (r) => r.source === 'temporal_today' || r.target === 'temporal_today',
  );
  results.push(['temporal_today NOT in relations', !todayInRels]);
  const modernArkaim = rels.some(
    (r) =>
      String(r.source).toLowerCase().includes('modernity') &&
      String(r.target).toLowerCase().includes('arkaim'),
  );
  results.push(['Modernity→Arkaim relation ABSENT', !modernArkaim]);
  const anchor = chain.nodes.find((n) => n.is_anchor === true || n.id === 'temporal_arkaim_era');
  const cats = anchor.provenance.map((t) => t.category).sort();
  results.push(['anchor dual provenance (AUTHOR_CANON+EXTERNAL_SOURCE)', JSON.stringify(cats) === JSON.stringify(['AUTHOR_CANON', 'EXTERNAL_SOURCE'])]);

  // /nodes: полный каталог (13 = 12 эпох + today); today — HYPOTHESIS, не якорь.
  const nodesResp = await req('GET', '/book/temporal/nodes');
  const nodesArr = Array.isArray(nodesResp.json.data)
    ? nodesResp.json.data
    : nodesResp.json.data.nodes ?? [];
  const todayFull = nodesArr.find((n) => n.id === 'temporal_today');
  results.push(['/nodes total = 13 (включая today)', nodesArr.length === 13]);
  results.push(['today: HYPOTHESIS provenance', todayFull.provenance.some((x) => x.category === 'HYPOTHESIS')]);
  results.push(['today: is_anchor=false', todayFull.is_anchor === false]);
}

// 2. Provenance-словарь FE == BE (зеркало)
{
  const feSrc = readFileSync('src/shared/ui/ProvenanceBadge.tsx', 'utf8');
  const be = parseBeDict();
  const feDict = {};
  const re = /([A-Z_]+):\s*\{\s*label:\s*'([^']+)',\s*color:\s*'([^']+)'/g;
  let m;
  while ((m = re.exec(feSrc)) !== null) feDict[m[1]] = { label: m[2], color: m[3] };
  const feKeys = Object.keys(feDict).filter((k) => k !== 'UNKNOWN' || true);
  const beKeys = Object.keys(be);
  const feOnly = feKeys.filter((k) => !beKeys.includes(k));
  const beOnly = beKeys.filter((k) => !feKeys.includes(k));
  const labelMismatch = Object.keys(be).filter((k) => feDict[k] && JSON.stringify(feDict[k]) !== JSON.stringify(be[k]));
  results.push([`FE dict keys == BE dict keys (feOnly=[${feOnly}] beOnly=[${beOnly}])`, feOnly.length === 0 && beOnly.length === 0]);
  results.push([`FE label/color == BE label/color (mismatch=[${labelMismatch}])`, labelMismatch.length === 0]);
}

// 3. Reader-сессия + M10.2 RBAC 403 + A2 422
{
  let cookieToUse = '';
  // eslint-disable-next-line prefer-const
  let ck2 = '';
  const reg = await req('POST', '/auth/register', {
    username: 'f3_followup_live',
    display_name: 'f3_followup_live',
  });
  results.push(['register reader session', reg.status === 200 || reg.status === 201]);
  const ck = reg.setCookie ? reg.setCookie.split(';')[0] : '';
  const regOk = reg.status === 200 || reg.status === 201;
  if (!regOk) {
    // username может быть занят прошлым прогоном — это тоже валидная сессия
    // (409), но cookie нет; повторяем с уникальным суффиксом.
    const reg2 = await req('POST', '/auth/register', {
      username: 'f3_followup_' + Date.now(),
      display_name: 'f3_followup_live',
    });
    results.push(['register retry (unique)', reg2.status === 200 || reg2.status === 201]);
    ck2 = reg2.setCookie ? reg2.setCookie.split(';')[0] : '';
    results.push(['session cookie present (retry)', ck2.length > 0]);
    cookieToUse = ck2;
  } else {
    results.push(['session cookie present', ck.length > 0]);
    cookieToUse = ck;
  }
  for (const p of ['scan', 'fnd_test/confirm', 'fnd_test/reject']) {
    const r = await req('POST', `/book/temporal/pending-updates/${p}`, p === 'scan' ? {} : { reason: 'x' }, cookieToUse);
    results.push([`reader 403 on ${p}`, r.status === 403]);
  }
  const ask = await req('POST', '/book/ask', { question: 'аб' }, cookieToUse);
  results.push(['A2: question len=2 → 422', ask.status === 422]);
}

// ── Итог ──
let ok = true;
for (const [name, r] of results) {
  console.log((r ? 'PASS' : 'FAIL') + ' - ' + name);
  ok = ok && r;
}
console.log('LIVE_RESULT: ' + (ok ? 'PASS' : 'FAIL'));
process.exit(ok ? 0 : 1);

/**
 * f3-live-smoke.mjs — live-проверка F3-вертикали «Время мира» (F3 audit §DoD).
 * Полный цикл через реальные backend-контракты (как это сделает frontend).
 * Аналог scripts/f2-live-smoke.mjs, расширенный под temporal-экраны.
 */
const BASE = 'http://localhost:8642';
const results = [];

function check(name, cond, extra = '') {
  results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) process.exitCode = 1;
}

const j = (r) => r.json();

// ── Reader: регистрация (cookie-сессия) ──
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `f3_smoke_${Date.now()}` }),
});
const cookie = (reg.headers.get('set-cookie') || '').split(';')[0];
check('1. register → 200 + cookie', reg.status === 200 && !!cookie);
const H = { 'Content-Type': 'application/json', cookie };

// ── Экран «Время мира»: цепочка эпох ──
const chain = await fetch(`${BASE}/book/temporal/chain`, { headers: H }).then(j);
check(
  '2. GET /chain → enveloped {data: {nodes, relations, stats}}',
  chain.ok === true && Array.isArray(chain.data.nodes) && Array.isArray(chain.data.relations),
  `${chain.data?.stats?.nodes} эпох, ${chain.data?.stats?.relations} связей`,
);
check(
  '3. якорь Аркаима в цепочке с двойным provenance (B1/C1: AUTHOR_CANON + EXTERNAL_SOURCE)',
  (() => {
    const anchor = (chain.data.nodes || []).find((n) => n.is_anchor);
    if (!anchor) return false;
    const cats = (anchor.provenance || []).map((p) => p.category);
    return cats.includes('AUTHOR_CANON') && cats.includes('EXTERNAL_SOURCE');
  })(),
);

// ── Узлы: 12 эпох + temporal_today (точка наблюдателя) ──
const nodes = await fetch(`${BASE}/book/temporal/nodes`, { headers: H }).then(j);
check(
  '4. GET /nodes → 13 узлов (12 эпох + today)',
  nodes.ok === true && nodes.data.length === 13,
  `total=${nodes.total}`,
);
const today = (nodes.data || []).find((n) => n.id === 'temporal_today');
check(
  '5. temporal_today — точка наблюдателя (HYPOTHESIS, не is_anchor)',
  !!today && today.provenance?.[0]?.category === 'HYPOTHESIS' && today.is_anchor === false,
);

// ИНВАРИАНТ ADR §5: today НЕ связан с эпохами в backend-данных
const todayInChain = JSON.stringify(chain.data.relations).includes('temporal_today');
check(
  '6. ИНВАРИАНТ: нет relation для temporal_today в цепочке (Present→Arkaim не синтезирован backend-ом)',
  todayInChain === false,
);

// ── Контекст эпохи ──
const ctx = await fetch(`${BASE}/book/temporal/context/arkaim_era`, { headers: H }).then(j);
check(
  '7. GET /context/arkaim_era → {temporal_node, epoch, events, characters, technologies}',
  ctx.ok === true && !!ctx.data.epoch && Array.isArray(ctx.data.events),
  `events=${ctx.data?.event_count}, chars=${ctx.data?.character_count}`,
);

// ── Сценарии будущего (reader-гейт; без LLM-ключей) ──
const fe = await fetch(`${BASE}/book/temporal/future-extrapolation`, {
  method: 'POST',
  headers: H,
  body: JSON.stringify({ prompt: 'что будет с наследием Аркаима', max_futures: 3 }),
}).then(j);
check(
  '8. POST /future-extrapolation → scenarios с provenance FUTURE_EXTRAPOLATION',
  fe.ok === true &&
    fe.data.scenarios?.length > 0 &&
    (fe.data.provenance || []).some((p) => p.category === 'FUTURE_EXTRAPOLATION'),
  `${fe.data?.scenarios?.length} сценариев, note=${fe.data?.provenance_note?.slice(0, 40)}`,
);
check(
  '9. сценарий — compatibility/risk поля для UI',
  fe.data.scenarios[0] && typeof fe.data.scenarios[0].compatibility_score === 'number' && !!fe.data.scenarios[0].risk_level,
);

// ── M10.2-очередь: reader-просмотр (reader+: list/stats/history) ──
const pu = await fetch(`${BASE}/book/temporal/pending-updates`, { headers: H }).then(j);
check(
  '10. GET /pending-updates (reader) → {ok, data, total}',
  pu.ok === true && Array.isArray(pu.data) && typeof pu.total === 'number',
);
const st = await fetch(`${BASE}/book/temporal/pending-updates/stats`, { headers: H }).then(j);
check(
  '11. GET /stats → {pending, confirmed, rejected}',
  st.ok === true && typeof st.data.pending === 'number',
  `pending=${st.data?.pending}`,
);

// ── RBAC-границы: reader НЕ может confirm/scan ──
const rConfirm = await fetch(`${BASE}/book/temporal/pending-updates/whatever/confirm`, {
  method: 'POST',
  headers: H,
  body: '{}',
});
check('12. reader → 403 на confirm (RBAC M10.2)', rConfirm.status === 403);
const rScan = await fetch(`${BASE}/book/temporal/pending-updates/scan`, {
  method: 'POST',
  headers: H,
  body: '{}',
});
check('13. reader → 403 на scan', rScan.status === 403);

// ── Без сессии: temporal-чтение открыто (RBAC-матрица: roles:[] = публичный GET;
// writer-gейты — только на мутациях). Живой факт: /chain отвечает 200 без cookie. ──
const noAuth = await fetch(`${BASE}/book/temporal/chain`);
const noAuthBody = await noAuth.json().catch(() => null);
check(
  '14. /chain без сессии → 200 (публичное чтение temporal — факт матрицы)',
  noAuth.status === 200 && noAuthBody?.ok === true && Array.isArray(noAuthBody?.data?.nodes),
);

console.log(results.join('\n'));
const fails = results.filter((r) => r.startsWith('FAIL')).length;
console.log(`\nF3 live-smoke: ${results.length - fails}/${results.length} PASS`);
if (fails > 0) process.exit(1);

/** forensic-audit-temporal.mjs — НЕЗАВИСИМЫЕ live-проверки аудита B1+C1. Не опирается на скрипт этапа. */
const BASE = 'http://localhost:8642';
const results = [];
const check = (id, name, cond, evidence) => {
  results.push({ id, name, cond, evidence });
  console.log(`${cond ? 'PASS' : 'FAIL'} [${id}] ${name}${evidence !== undefined ? '  | ' + JSON.stringify(evidence) : ''}`);
};

// ── /nodes: B1 ──
const nodesResp = await fetch(`${BASE}/book/temporal/nodes`);
const nodesBody = await nodesResp.json();
const nodes = nodesBody.data ?? [];
const ids = nodes.map((n) => n.id);
const today = nodes.find((n) => n.id === 'temporal_today');

check('B1.1', '/nodes 200 + ok', nodesResp.status === 200 && nodesBody.ok === true, { total: nodesBody.total });
check('B1.2', 'temporal_today присутствует', ids.includes('temporal_today'));
check('B1.3', 'today ровно один, последним (canonical order)', ids.filter((x) => x === 'temporal_today').length === 1 && ids[ids.length - 1] === 'temporal_today');
check('B1.4', 'today: HYPOTHESIS (observation point, не epoch)', today && today.provenance?.[0]?.category === 'HYPOTHESIS' && today.provenance?.[0]?.source_level === 'SYSTEM_INTERPRETATION', today?.provenance?.[0]);
check('B1.5', 'today: era_id пуст (не историческая эпоха), precision EXACT', today && today.era_id === '' && today.precision === 'EXACT');
check('B1.6', 'today: is_anchor=false, bounds 2025 CE', today && today.is_anchor === false && today.bounds?.start === '2025 CE');
check('B1.7', 'историческая ось в /nodes не изменилась: 12 эпох', ids.length === 13 && ids.filter((x) => x !== 'temporal_today').length === 12);
check('B1.8', 'нет дубля-anchor: temporal_arkaim_anchor отсутствует', !ids.includes('temporal_arkaim_anchor'));

// today не имеет временных связей: проверяем через /reconstruct от today и через все chain-рёбра
const recResp = await fetch(`${BASE}/book/temporal/reconstruct`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ source: 'temporal_today', target: 'temporal_arkaim_era', direction: 'FORWARD', max_depth: 5 }),
});
const recBody = await recResp.json();
check('B1.9', 'today→arkaim_era: путей НЕТ (узел без relations)', recBody?.data?.paths_found === 0, { paths_found: recBody?.data?.paths_found });

// ── /chain: C1 (оба направления) ──
for (const dir of ['FORWARD', 'BACKWARD']) {
  const r = await fetch(`${BASE}/book/temporal/chain?direction=${dir}`);
  const body = await r.json();
  const chain = body.data ?? {};
  const anchor = (chain.nodes ?? []).find((n) => n.id === 'temporal_arkaim_era');
  const rels = chain.relations ?? [];
  const cats = (anchor?.provenance ?? []).map((p) => p.category);

  check(`C1.${dir}.1`, `${dir}: 200 + ok`, r.status === 200 && body.ok === true);
  check(`C1.${dir}.2`, `${dir}: канонический якорь temporal_arkaim_era в chain`, !!anchor);
  check(`C1.${dir}.3`, `${dir}: provenance AUTHOR_CANON + EXTERNAL_SOURCE (как движок)`, cats.includes('AUTHOR_CANON') && cats.includes('EXTERNAL_SOURCE'), cats);
  const canon = (anchor?.provenance ?? []).find((p) => p.category === 'AUTHOR_CANON');
  const ext = (anchor?.provenance ?? []).find((p) => p.category === 'EXTERNAL_SOURCE');
  check(`C1.${dir}.4`, `${dir}: источники КНИГА.md / ARCHAEOLOGY.json (те же, что ArkaimAnchor)`, canon?.source_title === 'КНИГА.md' && ext?.source_title === 'ARCHAEOLOGY.json', { canon: canon?.source_title, ext: ext?.source_title });
  check(`C1.${dir}.5`, `${dir}: confidence 0.85 (как reconstruction_engine:595)`, anchor?.confidence === 0.85, anchor?.confidence);
  check(`INV.${dir}.1`, `${dir}: temporal_today НЕ в исторической оси`, !(chain.nodes ?? []).some((n) => n.id === 'temporal_today'));
  check(`INV.${dir}.2`, `${dir}: Present→Arkaim отсутствует (ни source, ни target)`, rels.every((x) => x.source_id !== 'temporal_today' && x.target_id !== 'temporal_today'));
  check(`INV.${dir}.3`, `${dir}: ось неизменна — 12 узлов, 11 рёбер, все PRECEDES`, (chain.nodes ?? []).length === 12 && rels.length === 11 && rels.every((x) => x.relation_type === 'PRECEDES'));
  check(`INV.${dir}.4`, `${dir}: FORWARDBACKWARD = traversal одного и того же множества PRECEDES`, true);
  const relIds = rels.map((x) => `${x.source_id}->${x.target_id}`).sort();
  const otherDir = dir === 'FORWARD' ? 'BACKWARD' : 'FORWARD';
  const r2 = await fetch(`${BASE}/book/temporal/chain?direction=${otherDir}`);
  const relIds2 = ((await r2.json()).data?.relations ?? []).map((x) => `${x.source_id}->${x.target_id}`).sort();
  const same = JSON.stringify(relIds) === JSON.stringify(relIds2);
  results.push({ id: `INV.axis-same`, name: `FORWARD и BACKWARD содержат ОДНО И ТО ЖЕ множество рёбер (traversal, не разные типы)`, cond: same, evidence: { same } });
  console.log(`${same ? 'PASS' : 'FAIL'} [INV.axis-same] FORWARD ≡ BACKWARD по множеству рёбер`);
  check(`C2.${dir}`, `${dir}: C2 реализован — рёбра несут DERIVED provenance (ADR TEMPORAL §4)`, rels.every((x) => x.provenance?.length === 1 && x.provenance[0].category === 'DERIVED' && x.provenance[0].notes === 'temporal precedence — derived from epoch ordering in canon'));
}

// ── legacy/M10.2 routes нетронуты (живые) ──
const pend = await fetch(`${BASE}/book/temporal/pending-updates`);
check('REG.1', 'M10.2 /pending-updates жив (не сломан этапом)', pend.status === 200 || pend.status === 403, { status: pend.status });
const fe = await fetch(`${BASE}/book/temporal/future-extrapolation`, { method: 'POST' });
check('REG.2', 'future-extrapolation на месте (401 без сессии = жив, reader-гейт)', fe.status === 401 || fe.status === 422, { status: fe.status });

// ── OpenAPI: структура неизменна, media-agnostic ──
const oa = await (await fetch(`${BASE}/openapi.json`)).json();
const temporalPaths = Object.keys(oa.paths).filter((p) => p.includes('/temporal'));
check('OAS.1', '14 temporal-путей (7 M4/M8 + 7 M10.2), нет новых/утерянных', temporalPaths.length === 14, temporalPaths);
const temporalSchemas = JSON.stringify(oa.paths).toLowerCase();
const mediaWords = ['comfy', 'workflow', 'image', 'video', 'audio', 'prompt_builder', 'sdxl', 'checkpoint', 'model_ref'];
const found = mediaWords.filter((w) => temporalSchemas.includes(w));
check('MEDIA.1', 'temporal-контракты не содержат media-backend полей (comfy/workflow/image/video/audio/...)', found.length === 0, { found });

const failed = results.filter((x) => !x.cond);
console.log(`\n=== ${results.length - failed.length}/${results.length} PASS ===`);
if (failed.length) { console.log('FAILED:', failed.map((f) => f.id).join(', ')); process.exit(1); }

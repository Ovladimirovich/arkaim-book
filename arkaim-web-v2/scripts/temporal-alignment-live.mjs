/** temporal-alignment-live.mjs — live-валидация B1+C1 по чеклисту владельца. */
const BASE = 'http://localhost:8642';
const fail = [];
const ok = (name, cond, extra = '') => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? '  ' + extra : ''}`);
  if (!cond) fail.push(name);
};

const nodesR = await fetch(`${BASE}/book/temporal/nodes`);
const nodes = await nodesR.json();
ok('/nodes 200', nodesR.status === 200);

const ids = nodes.data.map((n) => n.id);
ok('B1: temporal_today присутствует', ids.includes('temporal_today'), `total=${nodes.total}`);
ok('B1: total == len(data)', nodes.total === nodes.data.length);
ok('B1: today ровно один', ids.filter((i) => i === 'temporal_today').length === 1);
ok('B1: today последний (canonical order)', ids[ids.length - 1] === 'temporal_today');

const today = nodes.data.find((n) => n.id === 'temporal_today');
ok('B1: today category=HYPOTHESIS', today.provenance[0]?.category === 'HYPOTHESIS');
ok('B1: today is_anchor=false', today.is_anchor === false);
ok('B1: today era_id=""', today.era_id === '');

for (const dir of ['FORWARD', 'BACKWARD']) {
  const r = await fetch(`${BASE}/book/temporal/chain?direction=${dir}`);
  const body = await r.json();
  const chain = body.data;
  const nodeIds = chain.nodes.map((n) => n.id);

  ok(`C1[${dir}]: 200`, r.status === 200);
  ok(`C1[${dir}]: arkaim_era provenance обогащён`, (() => {
    const a = chain.nodes.find((n) => n.id === 'temporal_arkaim_era');
    const cats = (a.provenance ?? []).map((p) => p.category);
    return cats.includes('AUTHOR_CANON') && cats.includes('EXTERNAL_SOURCE');
  })(), (chain.nodes.find((n) => n.id === 'temporal_arkaim_era')?.provenance ?? []).map((p) => p.category).join('+'));
  ok(`C1[${dir}]: arkaim_era confidence=0.85`, chain.nodes.find((n) => n.id === 'temporal_arkaim_era')?.confidence === 0.85);
  ok(`INV[${dir}]: today НЕ в chain`, !nodeIds.includes('temporal_today'));
  ok(`INV[${dir}]: Present→Arkaim отсутствует`, chain.relations.every((r2) => r2.source_id !== 'temporal_today' && r2.target_id !== 'temporal_today'));
  ok(`INV[${dir}]: 12 узлов / 11 PRECEDES`, chain.nodes.length === 12 && chain.relations.length === 11 && chain.relations.every((r2) => r2.relation_type === 'PRECEDES'));
  ok(`C2[${dir}]: PRECEDES-рёбра = DERIVED (ADR TEMPORAL §4)`, chain.relations.every((r2) => r2.provenance.length === 1 && r2.provenance[0].category === 'DERIVED' && r2.provenance[0].notes === 'temporal precedence — derived from epoch ordering in canon'));
  ok(`INV[${dir}]: другие узлы не изменены`, chain.nodes.filter((n) => n.id !== 'temporal_arkaim_era').every((n) => n.provenance.length === 0 && n.confidence === 0.8));
}

// OpenAPI-структура путей не изменилась: все temporal-маршруты на месте (7 M4/M8 + 7 M10.2)
const oa = await (await fetch(`${BASE}/openapi.json`)).json();
const temporalPaths = Object.keys(oa.paths).filter((p) => p.includes('/temporal'));
const EXPECTED = [
  '/book/temporal/chain', '/book/temporal/node/{epoch_id}', '/book/temporal/context/{epoch_id}',
  '/book/temporal/reconstruct', '/book/temporal/chains', '/book/temporal/nodes',
  '/book/temporal/future-extrapolation', '/book/temporal/pending-updates/scan',
  '/book/temporal/pending-updates', '/book/temporal/pending-updates/stats',
  '/book/temporal/pending-updates/history', '/book/temporal/pending-updates/{finding_id}',
  '/book/temporal/pending-updates/{finding_id}/confirm', '/book/temporal/pending-updates/{finding_id}/reject',
];
const missing = EXPECTED.filter((p) => !temporalPaths.includes(p));
const extra = temporalPaths.filter((p) => !EXPECTED.includes(p));
ok('OpenAPI: все temporal-пути на месте, новых нет', missing.length === 0 && extra.length === 0, `count=${temporalPaths.length}${missing.length ? ' missing=' + missing : ''}${extra.length ? ' extra=' + extra : ''}`);

console.log(fail.length === 0 ? '\nALL LIVE CHECKS PASS' : `\nFAILED: ${fail.join('; ')}`);
process.exit(fail.length === 0 ? 0 : 1);

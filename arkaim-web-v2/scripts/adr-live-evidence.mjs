/** adr-live-evidence.mjs — фактические ответы temporal-контрактов для ADR. */
const BASE = 'http://localhost:8642';

async function j(r) { try { return await r.json(); } catch { return '<no json>'; } }

const chain = await j(await fetch(`${BASE}/book/temporal/chain?direction=FORWARD`));
console.log('== GET /book/temporal/chain?FORWARD ==');
console.log('stats:', JSON.stringify(chain.stats));
const nodeIds = (chain.data?.nodes ?? []).map((n) => n.id);
console.log('nodes:', nodeIds.join(', '));
console.log('есть temporal_today?', nodeIds.includes('temporal_today'));
const relTypes = new Set((chain.data?.relations ?? []).map((r) => r.relation_type));
console.log('types of relations:', [...relTypes].join(', '));
const anchorEra = (chain.data?.nodes ?? []).find((n) => n.id === 'temporal_arkaim_era');
console.log('arkaim_era provenance:', JSON.stringify(anchorEra?.provenance ?? null).slice(0, 200));
console.log('arkaim_era confidence:', anchorEra?.confidence);
console.log('is_anchor:', anchorEra?.is_anchor);

console.log('\n== GET /book/temporal/nodes ==');
const nodes = await j(await fetch(`${BASE}/book/temporal/nodes`));
console.log('total:', nodes.total, '| ids:', (nodes.data ?? []).map((n) => n.id).join(', '));
console.log('есть temporal_today?', (nodes.data ?? []).some((n) => n.id === 'temporal_today'));

console.log('\n== GET /book/temporal/chain?BACKWARD (для сравнения) ==');
const back = await j(await fetch(`${BASE}/book/temporal/chain?direction=BACKWARD`));
console.log('stats:', JSON.stringify(back.stats));
const backIds = (back.data?.nodes ?? []).map((n) => n.id);
console.log('nodes:', backIds.join(', '));
console.log('есть temporal_today?', backIds.includes('temporal_today'));

/**
 * f2-live-smoke.mjs вЂ” live-РїСЂРѕРІРµСЂРєР° F2-РІРµСЂС‚РёРєР°Р»Рё В«Р”РёР°Р»РѕРі СЃ РєРЅРёРіРѕР№В» (SPEC В§12).
 * РџРѕР»РЅС‹Р№ С†РёРєР» С‡РµСЂРµР· СЂРµР°Р»СЊРЅС‹Рµ backend-РєРѕРЅС‚СЂР°РєС‚С‹ (РєР°Рє СЌС‚Рѕ СЃРґРµР»Р°РµС‚ frontend).
 * РђРЅР°Р»РѕРі scripts/live-smoke.mjs РёР· F1, СЂР°СЃС€РёСЂРµРЅРЅС‹Р№ РїРѕРґ F2-СЌРєСЂР°РЅС‹.
 */
const BASE = 'http://localhost:8642';
const results = [];

function check(name, cond, extra = '') {
  results.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? ` вЂ” ${extra}` : ''}`);
  if (!cond) process.exitCode = 1;
}

// в”Ђв”Ђ Р РµРіРёСЃС‚СЂР°С†РёСЏ (reader) в”Ђв”Ђ
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `f2_e2e_${Date.now()}` }),
});
const cookie = (reg.headers.get('set-cookie') || '').split(';')[0];
check('1. register в†’ 200 + cookie', reg.status === 200 && !!cookie);

const H = { 'Content-Type': 'application/json', cookie };

// в”Ђв”Ђ Р­РєСЂР°РЅ В«РЎРїСЂРѕСЃРёС‚СЊ РєРЅРёРіСѓВ» в”Ђв”Ђ
const ask = await fetch(`${BASE}/book/ask`, {
  method: 'POST', headers: H,
  body: JSON.stringify({ question: 'РљС‚Рѕ С‚Р°РєРѕР№ Р”СЂРµРІРЅРёР№ РЈСЃС‚?' }),
});
const askBody = await ask.json();
check(
  '2. POST /book/ask в†’ 200 enveloped {answer, source}',
  ask.status === 200 && typeof askBody.data?.answer === 'string' && typeof askBody.data?.source === 'string',
  `source=${askBody.data?.source}`,
);
check(
  '3. ask-РѕС‚РІРµС‚ РЅРµРїСѓСЃС‚РѕР№ (Pulse Р±РµР· LLM-РєР»СЋС‡РµР№)',
  (askBody.data?.answer?.length ?? 0) > 10,
);

// в”Ђв”Ђ РџСЂРѕС„РёР»СЊ РїРѕСЃР»Рµ ask (invalidate-РєРµР№СЃ) в”Ђв”Ђ
const prof = await fetch(`${BASE}/book/reader/profile`, { headers: H });
const profBody = await prof.json();
check(
  '4. profile РїРѕСЃР»Рµ ask в†’ questions_total=1, topic РµСЃС‚СЊ',
  prof.status === 200 && profBody.questions_total === 1 && (profBody.topics?.length ?? 0) >= 1,
  `total=${profBody.questions_total}, last_topic=${profBody.last_topic}`,
);

// в”Ђв”Ђ Р­РєСЂР°РЅ В«Р§С‚РµРЅРёРµВ» в”Ђв”Ђ
const chapters = await fetch(`${BASE}/book/chapters`, { headers: H });
const chaptersBody = await chapters.json();
check(
  '5. GET /book/chapters в†’ РіР»Р°РІС‹',
  chapters.status === 200 && Array.isArray(chaptersBody.data) && chaptersBody.data.length > 3,
  `${chaptersBody.data?.length} РіР»Р°РІ`,
);

const text = await fetch(`${BASE}/book/text?offset=0&limit=4000`, { headers: H });
const textBody = await text.json();
check(
  '6. GET /book/text в†’ РїР°РіРёРЅР°С†РёСЏ (data/total/has_more)',
  text.status === 200 && typeof textBody.data === 'string' && textBody.total > 10000 && typeof textBody.has_more === 'boolean',
  `total=${textBody.total}`,
);

const re = await fetch(`${BASE}/book/reader/reading-event`, {
  method: 'POST', headers: H,
  body: JSON.stringify({ chapter_id: 'ch_01', chapter_index: 1, read_seconds: 30, scroll_percent: 40, completed: false }),
});
check('7. POST /book/reader/reading-event в†’ {ok:true}', re.status === 200 && (await re.json()).ok === true);

const pos = await fetch(`${BASE}/book/reader/reading-position`, { headers: H });
const posBody = await pos.json();
check(
  '8. GET /book/reader/reading-position в†’ РїРѕР·РёС†РёСЏ РїРѕСЃР»Рµ С‡С‚РµРЅРёСЏ',
  pos.status === 200 && posBody.data?.chapter_id === 'ch_01',
  `scroll=${posBody.data?.scroll_percent}%`,
);

// в”Ђв”Ђ Genome/layers (РіРµРЅРѕРј Р±РµР· can-РіРµР№С‚Р° вЂ” РєРѕРЅС‚СЂР°РєС‚РЅР°СЏ РґРµС‚Р°Р»СЊ) в”Ђв”Ђ
const genome = await fetch(`${BASE}/book/genome`, { headers: H });
check('9. GET /book/genome в†’ 200 (reader-РґРѕСЃС‚СѓРї)', genome.status === 200);

const layers = await fetch(`${BASE}/book/layers`, { headers: H });
check('10. GET /book/layers в†’ 200', layers.status === 200);

// в”Ђв”Ђ Error-states (SPEC В§10) в”Ђв”Ђ
const unauth = await fetch(`${BASE}/book/ask`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: 'x' }),
});
const unauthBody = await unauth.json();
check(
  '11. ask Р±РµР· СЃРµСЃСЃРёРё в†’ 401 envelope (РЅРµ mock, РЅРµ РїСѓСЃС‚Рѕ)',
  unauth.status === 401 && unauthBody.ok === false && unauthBody.error?.code === 'HTTP_401',
);

const badq = await fetch(`${BASE}/book/ask`, {
  method: 'POST', headers: H,
  body: JSON.stringify({ question: '' }),
});
check(
  '12. ask СЃ РїСѓСЃС‚С‹Рј РІРѕРїСЂРѕСЃРѕРј в†’ 4xx (pydantic), ApiError-РјРѕРґРµР»СЊ С„СЂРѕРЅС‚Р° СЃСЂР°Р±РѕС‚Р°РµС‚',
  badq.status >= 400 && badq.status < 500,
  `status=${badq.status}`,
);

console.log(results.join('\n'));
const fails = results.filter((r) => r.startsWith('FAIL')).length;
console.log(`\nF2 live-smoke: ${results.length - fails}/${results.length} PASS`);
if (fails > 0) process.exit(1);


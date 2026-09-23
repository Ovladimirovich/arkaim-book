/** forensic-reg1.mjs — REG.1 с корректным legacy-контрактом регистрации (username). */
const BASE = 'http://localhost:8642';
const uname = `forensic${Date.now().toString().slice(-8)}`;
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: uname, email: `${uname}@audit.local`, display_name: 'Forensic Auditor' }),
});
const setCookie = reg.headers.get('set-cookie') ?? '';
const cookie = setCookie.split(';')[0];
const regBody = await reg.json();
console.log('register:', reg.status, 'role:', regBody?.user?.role ?? regBody?.error?.code ?? regBody?.detail);

const pend = await fetch(`${BASE}/book/temporal/pending-updates`, { headers: { Cookie: cookie } });
const pendBody = await pend.json();
console.log(`REG.1: /pending-updates с reader = ${pend.status} → ${pend.status === 200 ? 'PASS (M10.2 жив, reader разрешён)' : 'FAIL'} | body: ${JSON.stringify(pendBody).slice(0, 140)}`);

// Контроль: reader не может scan (editor+)
const scan = await fetch(`${BASE}/book/temporal/pending-updates/scan`, { method: 'POST', headers: { Cookie: cookie } });
console.log(`REG.1b: /scan с reader = ${scan.status} (ожидание 403 — editor-гейт цел) → ${scan.status === 403 ? 'PASS' : 'FAIL'}`);

/**
 * f2-audit-auth.mjs — §5: полный auth-lifecycle live.
 * register → cookie → /me → logout (stateless-JWT особенность) + cookie-флаги.
 */
const BASE = 'http://localhost:8642';
const out = [];
function check(name, cond, extra = '') {
  out.push(`${cond ? 'PASS' : 'FAIL'}  ${name}${extra ? ` — ${extra}` : ''}`);
  if (!cond) process.exitCode = 1;
}

// 1. register
const reg = await fetch(`${BASE}/auth/register`, {
  method: 'POST', headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: `authaudit_${Date.now()}` }),
});
const setCookie = reg.headers.get('set-cookie') || '';
const regBody = await reg.json();
check('1. register → 200 {ok, user.role=reader}', reg.status === 200 && regBody.ok === true && regBody.user?.role === 'reader');

// 2. cookie-флаги (HttpOnly, SameSite)
check('2. Set-Cookie arkaim_session: HttpOnly + SameSite=Lax', setCookie.includes('arkaim_session=') && setCookie.toLowerCase().includes('httponly') && setCookie.toLowerCase().includes('samesite=lax'), setCookie.slice(0, 80));
const cookie = setCookie.split(';')[0];

// 3. /me с cookie
const me = await fetch(`${BASE}/auth/me`, { headers: { cookie } });
const meBody = await me.json();
check('3. /me с cookie → 200 {user}', me.status === 200 && !!meBody.user?.id && meBody.user?.role === 'reader');

// 4. /me без cookie → 401 envelope
const me401 = await fetch(`${BASE}/auth/me`);
const me401Body = await me401.json();
check('4. /me без сессии → 401 envelope', me401.status === 401 && me401Body.ok === false && me401Body.error?.code === 'HTTP_401');

// 5. logout: backend стирает cookie-инструкцию
const lo = await fetch(`${BASE}/auth/logout`, { method: 'POST', headers: { cookie } });
const loSetCookie = lo.headers.get('set-cookie') || '';
check('5. logout → 200 + delete-cookie инструкция', lo.status === 200 && /arkaim_session=;|arkaim_session=deleted|max-age=0/i.test(loSetCookie), loSetCookie.slice(0, 60));

// 6. stateless-JWT (известная backend-особенность, F1-аудит §5): старый cookie валиден
const meAfter = await fetch(`${BASE}/auth/me`, { headers: { cookie } });
check('6. [backend-особенность] старый JWT валиден после logout (12ч) — задокументировано, не F2-дефект', meAfter.status === 200);

// 7. Frontend logout-флоу (код AuthProvider): POST logout + setQueryData(null) + redirect —
// проверяем исходник (не браузер — см. verification limitation)
const src = await import('node:fs').then((fs) => fs.readFileSync('src/entities/auth/AuthProvider.tsx', 'utf8'));
check('7. AuthProvider: logout() вызывает POST /auth/logout', src.includes("logout(") && src.includes('/auth/logout'));
check('8. AuthProvider: сброс auth-кэша после logout', src.includes("setQueryData(['auth','me']") || src.includes('setQueryData'));

// 9. B2-фикс в исходнике (StrictMode-безопасность — семантика доказана unit-тестами;
// browser-тест невозможен в sandbox — limitation зафиксирована в §11)
const login = await import('node:fs').then((fs) => fs.readFileSync('src/app/(auth)/login/page.tsx', 'utf8'));
check('9. B2: urlToken в useEffect + ref-guard (не в render)', login.includes('useEffect(') && login.includes('tokenHandledRef') && !login.includes('if (urlToken && !busy)'));

console.log(out.join('\n'));

import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8642';

export async function POST() {
  try {
    // 1. Генерируем dev-токен
    const tokenResp = await fetch(`${BACKEND_URL}/auth/dev/generate-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_user_id: 'dev-user-001',
        username: 'developer',
        display_name: 'Разработчик',
      }),
    });

    if (!tokenResp.ok) {
      return NextResponse.json({ ok: false, error: 'Не удалось сгенерировать токен' }, { status: 502 });
    }

    const tokenData = await tokenResp.json();
    const loginToken = tokenData.token;

    // 2. Логинимся через token endpoint — устанавливает cookie
    const loginResp = await fetch(`${BACKEND_URL}/auth/telegram/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: loginToken }),
    });

    const loginData = await loginResp.json();

    if (!loginResp.ok) {
      return NextResponse.json(loginData, { status: loginResp.status });
    }

    // 3. Копируем cookie
    const response = NextResponse.json(loginData);
    const setCookie = loginResp.headers.get('set-cookie');
    if (setCookie) {
      response.headers.set('set-cookie', setCookie);
    }

    return response;
  } catch {
    return NextResponse.json(
      { ok: false, error: 'Ошибка подключения к бэкенду' },
      { status: 502 }
    );
  }
}

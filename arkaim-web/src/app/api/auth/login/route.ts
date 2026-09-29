import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8642';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const resp = await fetch(`${BACKEND_URL}/auth/telegram/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const result = await resp.json();

    if (!resp.ok) {
      return NextResponse.json(result, { status: resp.status });
    }

    // Копируем cookie из ответа бэкенда
    const response = NextResponse.json(result);
    const setCookie = resp.headers.get('set-cookie');
    if (setCookie) {
      response.headers.set('set-cookie', setCookie);
    }

    return response;
  } catch (error) {
    return NextResponse.json(
      { ok: false, error: 'Ошибка подключения к бэкенду' },
      { status: 502 }
    );
  }
}

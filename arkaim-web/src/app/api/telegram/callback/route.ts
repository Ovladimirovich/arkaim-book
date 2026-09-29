import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8642';

export async function POST(request: NextRequest) {
  try {
    // Telegram Widget отправляет form-urlencoded POST
    const text = await request.text();
    const params = new URLSearchParams(text);

    // Конвертируем в JSON для бэкенда
    const data: Record<string, string> = {};
    params.forEach((value, key) => {
      data[key] = value;
    });

    // Отправляем на бэкенд
    const resp = await fetch(`${BACKEND_URL}/auth/telegram/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    const result = await resp.json();

    if (!resp.ok) {
      return NextResponse.json(result, { status: resp.status });
    }

    // Создаём ответ с cookie от бэкенда
    const response = NextResponse.json(result);

    // Копируем cookie из ответа бэкенда
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

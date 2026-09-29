import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8642';

export async function POST() {
  try {
    const resp = await fetch(`${BACKEND_URL}/auth/logout`, {
      method: 'POST',
    });

    const result = await resp.json();

    const response = NextResponse.json(result);
    const setCookie = resp.headers.get('set-cookie');
    if (setCookie) {
      response.headers.set('set-cookie', setCookie);
    }

    return response;
  } catch {
    // Даже если бэкенд недоступен — удаляем cookie на клиенте
    const response = NextResponse.json({ ok: true });
    response.headers.set(
      'set-cookie',
      'arkaim_session=; Path=/; Max-Age=0; HttpOnly'
    );
    return response;
  }
}

/**
 * auth.test.ts — auth-контракты против mock-транспорта (не мок-данных!):
 * ответы соответствуют фактическому JSON backend (F1_SPEC §5, §10).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

// ── Mock transport: перехват fetch, ответы = фактические контракты ──
const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import { getMe, register } from '@/shared/api/contracts/auth';

afterEach(() => {
  fetchMock.mockReset();
});

describe('getMe', () => {
  it('200 + {user} → AuthUser', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ user: { id: 'u1', role: 'editor', username: 'iva', provider: 'email' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const me = await getMe();
    expect(me?.id).toBe('u1');
    expect(me?.role).toBe('editor');
  });

  it('401 {detail} → null (не залогинен)', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Не авторизован' }), { status: 401 }),
    );
    const me = await getMe();
    expect(me).toBeNull();
  });

  it('network → throw ApiError NETWORK', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));
    await expect(getMe()).rejects.toMatchObject({ code: 'NETWORK' });
  });
});

describe('register', () => {
  it('200 → {ok, user: reader} + cookie-запрос same-origin', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true, user: { id: 'u2', role: 'reader', username: 'novichok' } }), {
        status: 200,
      }),
    );
    const r = await register({ username: 'novichok' });
    expect(r.user.role).toBe('reader');
    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe('/auth/register');
    expect(call[1].method).toBe('POST');
    expect(call[1].credentials).toBe('same-origin');
    expect(JSON.parse(call[1].body).username).toBe('novichok');
  });

  it('409 {detail} → ApiError HTTP_409', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Пользователь с таким именем уже существует' }), { status: 409 }),
    );
    await expect(register({ username: 'dup' })).rejects.toMatchObject({ status: 409, code: 'HTTP_409' });
  });
});

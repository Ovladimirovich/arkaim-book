import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

import { AuthProvider, useAuth } from '@/app/providers';

type State = { user: { id: string; role: string } | null; loading: boolean };

function Probe() {
  const { user, loading } = useAuth();
  const state: State = { user: user ? { id: user.id, role: user.role } : null, loading };
  return <div data-testid="state">{JSON.stringify(state)}</div>;
}

function readState(): State {
  return JSON.parse(screen.getByTestId('state').textContent || '{}') as State;
}

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: async () => body,
  } as Response;
}

const VALID_USER = { id: 'u-real', role: 'admin', username: 'developer', display_name: 'Разработчик', provider: 'telegram' };

function mockFetch(impl: (url: string, init?: RequestInit) => Promise<Response> | Response) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => impl(String(input), init));
  global.fetch = fn as unknown as typeof fetch;
  return fn;
}

describe('AuthProvider', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('uses existing cookie session from /auth/me and does not call dev-login', async () => {
    const fetchMock = mockFetch(url => {
      if (url === '/auth/me') return jsonResponse({ user: VALID_USER });
      throw new Error(`unexpected fetch: ${url}`);
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(readState().loading).toBe(false));
    expect(readState().user).toEqual({ id: 'u-real', role: 'admin' });
    expect(fetchMock.mock.calls.map(c => String(c[0]))).toEqual(['/auth/me']);
    expect(JSON.parse(localStorage.getItem('arkaim_user') || '{}').id).toBe('u-real');
  });

  it('falls back to dev-login when /auth/me returns 401 and establishes the session', async () => {
    const fetchMock = mockFetch(url => {
      if (url === '/auth/me') return jsonResponse({ detail: 'Не авторизован' }, false, 401);
      if (url === '/api/auth/dev-login') return jsonResponse({ ok: true, user: VALID_USER });
      throw new Error(`unexpected fetch: ${url}`);
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(readState().loading).toBe(false));
    expect(readState().user).toEqual({ id: 'u-real', role: 'admin' });
    expect(fetchMock.mock.calls.map(c => String(c[0]))).toEqual(['/auth/me', '/api/auth/dev-login']);
  });

  it('never trusts a stale localStorage cache: session is re-verified against backend', async () => {
    // Симулируем «вчерашний» кэш при истёкшей HttpOnly-cookie — источник 401-шторма.
    localStorage.setItem('arkaim_user', JSON.stringify({ id: 'stale', role: 'admin', provider: 'dev' }));

    const fetchMock = mockFetch(url => {
      if (url === '/auth/me') return jsonResponse({ detail: 'Не авторизован' }, false, 401);
      if (url === '/api/auth/dev-login') return jsonResponse({ ok: true, user: VALID_USER });
      throw new Error(`unexpected fetch: ${url}`);
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(readState().loading).toBe(false));
    expect(fetchMock).toHaveBeenCalled();
    expect(readState().user?.id).toBe('u-real');
    expect(localStorage.getItem('arkaim_user')).not.toContain('stale');
  });

  it('reports unauthenticated (user=null) when backend answers but session cannot be established', async () => {
    mockFetch(url => {
      if (url === '/auth/me') return jsonResponse({ detail: 'Не авторизован' }, false, 401);
      if (url === '/api/auth/dev-login') return jsonResponse({ ok: false, error: 'no' }, false, 502);
      throw new Error(`unexpected fetch: ${url}`);
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(readState().loading).toBe(false));
    expect(readState().user).toBeNull();
    expect(localStorage.getItem('arkaim_user')).toBeNull();
  });

  it('keeps the dev fallback only when backend is unreachable', async () => {
    mockFetch(() => {
      throw new TypeError('Failed to fetch');
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(readState().loading).toBe(false));
    expect(readState().user).toEqual({ id: 'dev-user-001', role: 'admin' });
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError } from '@/shared/lib/api';

/**
 * Контракт поведения `request()` после API-CLIENT-FIX-1.
 *
 * 401/403/404 и сетевые ошибки НЕ подменяются мок-данными: вызывающий код
 * (страницы) обязан увидеть настоящую ошибку. Подмена сохранена только для
 * 5xx и только вне путей `/book/reader/history*` и `/book/comfyui/*`.
 */

function jsonResp(status: number, body: unknown = {}): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    headers: new Headers({ 'content-type': 'application/json' }),
  } as Response;
}

function setFetch(impl: () => Promise<Response> | Response) {
  const fn = vi.fn(() => impl());
  global.fetch = fn as unknown as typeof fetch;
  return fn;
}

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(document, 'cookie', { value: '', writable: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('makes GET request with correct URL', async () => {
    const mockFetch = setFetch(() => jsonResp(200, { data: 'test' }));

    const result = await api.get('/test');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/test'),
      expect.objectContaining({ method: 'GET' }),
    );
    expect(result).toEqual({ data: 'test' });
  });

  it('makes POST request with body', async () => {
    const mockFetch = setFetch(() => jsonResp(200, { ok: true }));

    await api.post('/test', { name: 'test' });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/test'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'test' }),
      }),
    );
  });

  it('throws ApiError on non-OK response', async () => {
    setFetch(() => jsonResp(500, { detail: 'Server error' }));

    await expect(api.get('/boom')).rejects.toThrow(ApiError);
  });

  // ── FIX-1 §1: 401/403/404 — настоящая ошибка, НЕ мок ──────────

  it('throws ApiError on 401 instead of returning an empty object', async () => {
    setFetch(() => jsonResp(401, { detail: 'Не авторизован' }));

    // До фикса возвращался `{}` — потеря сессии была невидимой.
    await expect(api.get('/protected')).rejects.toThrow(ApiError);
  });

  it('401 error carries status and the backend detail', async () => {
    setFetch(() => jsonResp(401, { detail: 'Не авторизован' }));

    // ApiError.message — «HTTP <status>»; полезная нагрузка backend в .data.
    const err = await api.get('/protected').catch(e => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as InstanceType<typeof ApiError>).status).toBe(401);
    expect((err as InstanceType<typeof ApiError>).data).toEqual({ detail: 'Не авторизован' });
  });

  it('throws ApiError on 403', async () => {
    setFetch(() => jsonResp(403, { detail: 'Недостаточно прав' }));

    await expect(api.get('/admin-only')).rejects.toMatchObject({ status: 403 });
  });

  it('throws ApiError on 404', async () => {
    setFetch(() => jsonResp(404, { detail: 'Not Found' }));

    // До фикса 404 подменялся моком и экран выглядел рабочим.
    await expect(api.get('/missing')).rejects.toThrow(ApiError);
  });

  it('401 on a heavily mocked path still throws (no mock substitution)', async () => {
    setFetch(() => jsonResp(401));

    // /book/genome есть в MOCK_DATA — именно такие пути раньше молчали.
    await expect(api.get('/book/genome')).rejects.toThrow(ApiError);
  });

  it('404 on a heavily mocked path still throws (no mock substitution)', async () => {
    setFetch(() => jsonResp(404));

    await expect(api.get('/book/community/notifications')).rejects.toThrow(ApiError);
  });

  // ── FIX-1 §3: сетевая ошибка не даёт пустого объекта / мока ───

  it('propagates network errors instead of returning mocks or {}', async () => {
    setFetch(() => Promise.reject(new TypeError('Failed to fetch')));

    await expect(api.get('/book/genome')).rejects.toThrow();
  });

  it('network error is not an ApiError with a fabricated status', async () => {
    setFetch(() => Promise.reject(new TypeError('Failed to fetch')));

    const err = await api.get('/book/genome').catch(e => e);
    expect(err).toBeInstanceOf(TypeError);
  });

  // ── FIX-1 §2: сессия только через cookie, без Bearer ──────────

  it('sends same-origin credentials and never a Bearer header from cookies', async () => {
    // HttpOnly-cookie из JS не читается; ручной Bearer лишь ломал сессию.
    Object.defineProperty(document, 'cookie', {
      value: 'arkaim_session=fake-token',
      writable: true,
    });
    const mockFetch = setFetch(() => jsonResp(200, { ok: true }));

    await api.get('/book/reader/profile');

    const [, init] = mockFetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.credentials).toBe('same-origin');
    const headers = init.headers as Record<string, string>;
    expect(headers['Authorization']).toBeUndefined();
  });

  // ── FIX-1 §4: запрет моков для history* и comfyui ─────────────

  it('never mocks /book/reader/history even on 5xx', async () => {
    setFetch(() => jsonResp(500));

    await expect(api.get('/book/reader/history?limit=5')).rejects.toThrow(ApiError);
  });

  it('never mocks /book/reader/history/full even on 5xx', async () => {
    setFetch(() => jsonResp(500));

    await expect(api.get('/book/reader/history/full?limit=20')).rejects.toThrow(ApiError);
  });

  it('never mocks /book/comfyui/status even on 5xx', async () => {
    setFetch(() => jsonResp(500));

    await expect(api.get('/book/comfyui/status')).rejects.toThrow(ApiError);
  });

  // ── ERROR-STATE-DISPLAY-1 §5: запрет моков для содержания и профиля ──

  it('never mocks /book/chapters even on 5xx', async () => {
    setFetch(() => jsonResp(500));

    await expect(api.get('/book/chapters')).rejects.toMatchObject({ status: 500 });
  });

  it('never mocks /book/chapters/{id} even on 5xx', async () => {
    setFetch(() => jsonResp(500));

    await expect(api.get('/book/chapters/abc123')).rejects.toThrow(ApiError);
  });

  it('never mocks /book/reader/profile even on 5xx', async () => {
    setFetch(() => jsonResp(500));

    await expect(api.get('/book/reader/profile')).rejects.toMatchObject({ status: 500 });
  });

  // ── Сохранённое поведение: 5xx на обычных путях ───────────────────────

  // Важно: `MOCK_DATA` заполняется только при NODE_ENV === 'development',
  // а vitest работает в 'test' — поэтому здесь таблица моков пуста и
  // проверяется не сама подмена, а то, что 5xx НЕ теряется молча:
  // либо отдаётся мок (dev), либо бросается настоящая ошибка.

  it('never swallows 5xx: either mocks (dev) or throws a real error', async () => {
    setFetch(() => jsonResp(500, { detail: 'Server error' }));

    const outcome = await api.get('/book/genome').then(
      value => ({ mocked: value }),
      err => ({ error: err as InstanceType<typeof ApiError> }),
    );

    if ('error' in outcome) {
      expect(outcome.error).toBeInstanceOf(ApiError);
      expect(outcome.error.status).toBe(500);
    } else {
      // Dev-подмена допустима, но пустой объект — нет.
      expect(outcome.mocked).toBeTruthy();
      expect(outcome.mocked).not.toEqual({});
    }
  });

  it('does not fabricate data on 5xx when no mock exists', async () => {
    setFetch(() => jsonResp(500, { detail: 'Server error' }));

    await expect(api.get('/book/film/list')).rejects.toThrow(ApiError);
  });

  it('5xx on a never-mocked path always throws, regardless of dev mode', async () => {
    setFetch(() => jsonResp(500, { detail: 'Server error' }));

    await expect(api.get('/book/reader/history')).rejects.toMatchObject({ status: 500 });
  });
});


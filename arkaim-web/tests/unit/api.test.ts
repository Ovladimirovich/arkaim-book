import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, ApiError } from '@/shared/lib/api';

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock document.cookie
    Object.defineProperty(document, 'cookie', { value: '', writable: true });
  });

  it('makes GET request with correct URL', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: 'test' }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });
    global.fetch = mockFetch;

    const result = await api.get('/test');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/test'),
      expect.objectContaining({ method: 'GET' })
    );
    expect(result).toEqual({ data: 'test' });
  });

  it('makes POST request with body', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ok: true }),
      headers: new Headers({ 'content-type': 'application/json' }),
    });
    global.fetch = mockFetch;

    await api.post('/test', { name: 'test' });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/test'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'test' }),
      })
    );
  });

  it('throws ApiError on non-OK response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Not found' }),
    });

    await expect(api.get('/missing')).rejects.toThrow(ApiError);
  });

  it('returns empty object on 401 (dev mode)', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
    });

    const result = await api.get('/protected');
    expect(result).toEqual({});
  });
});

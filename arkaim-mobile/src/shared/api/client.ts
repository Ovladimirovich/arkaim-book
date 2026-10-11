/**
 * API клиент для мобильного приложения.
 * Использует expo-secure-store для хранения JWT.
 */
import * as SecureStore from 'expo-secure-store';

const API_BASE = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8642';

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync('arkaim_session');
}

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = await getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const resp = await fetch(url, { ...opts, headers });

    if (resp.status === 401) {
      throw new ApiError(401, 'Не авторизован');
    }

    if (!resp.ok) {
      let data: unknown;
      try { data = await resp.json(); } catch { data = null; }
      throw new ApiError(resp.status, `HTTP ${resp.status}`, data);
    }

    const contentType = resp.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return resp.json() as Promise<T>;
    }
    return resp.text() as unknown as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw err;
  }
}

export const api = {
  get: <T>(path: string, opts?: RequestInit) =>
    request<T>(path, { method: 'GET', ...opts }),

  post: <T>(path: string, body?: unknown, opts?: RequestInit) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined, ...opts }),

  delete: <T>(path: string, opts?: RequestInit) =>
    request<T>(path, { method: 'DELETE', ...opts }),
};

export async function setToken(token: string) {
  await SecureStore.setItemAsync('arkaim_session', token);
}

export async function clearToken() {
  await SecureStore.deleteItemAsync('arkaim_session');
}

export async function isLoggedIn(): Promise<boolean> {
  const token = await getToken();
  return !!token;
}

export { ApiError, API_BASE };

/**
 * client.ts — единый HTTP-клиент typed-contract-слоя (F1_SPEC §6).
 *
 * Правила:
 *  - credentials: same-origin (cookie arkaim_session — основной механизм сессии);
 *  - Authorization-override — только когда задан Bearer-токен (API-key тестер);
 *  - retry: 1 попытка на 5xx/network;
 *  - все ошибки → ApiError (никаких сырых Response наружу);
 *  - 401 не «мокается» НИКОГДА — наверх уходит ApiError.isAuthError (красная линия F1).
 *
 * Этот файл — одно из двух разрешённых мест сетевых вызовов (см. eslint-правила).
 */

import { ApiError, networkError, parseError, parseErrorBody, timeoutError } from './errors';
import { unwrap } from './envelope';

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: unknown;
  signal?: AbortSignal;
  /** Явный Bearer-токен (API-key режим). Иначе — cookie-сессия. */
  bearerToken?: string;
  timeoutMs?: number;
  retryOn5xx?: boolean;
}

const DEFAULT_TIMEOUT = 30_000;

let globalBearer: string | null = null;

/** Установить глобальный Bearer (используется API-key тестером). */
export function setBearer(token: string | null) {
  globalBearer = token;
}

async function once(method: string, path: string, opts: RequestOptions): Promise<unknown> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), opts.timeoutMs ?? DEFAULT_TIMEOUT);
  if (opts.signal) {
    opts.signal.addEventListener('abort', () => controller.abort(), { once: true });
  }
  try {
    const headers: Record<string, string> = {};
    if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
    const bearer = opts.bearerToken ?? globalBearer;
    if (bearer) headers['Authorization'] = `Bearer ${bearer}`;

    const resp = await fetch(path, {
      method: method,
      headers,
      credentials: 'same-origin',
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: controller.signal,
    });

    if (!resp.ok) {
      let body: unknown = null;
      try {
        body = await resp.json();
      } catch {
        /* тело не JSON — упадёт в parseErrorBody fallback */
      }
      throw parseErrorBody(resp.status, body);
    }

    try {
      return await resp.json();
    } catch (e) {
      throw parseError(e);
    }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (controller.signal.aborted) throw timeoutError();
    throw networkError(e);
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Typed-вызов endpoint'а. Разворачивает конверт согласно ENVELOPE_MAP.
 */
export async function apiCall<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const m = (opts.method ?? method).toUpperCase();
  let lastError: ApiError;
  const attempts = opts.retryOn5xx === false ? 1 : 2;
  for (let i = 1; i <= attempts; i++) {
    try {
      const raw = await once(m, path, opts);
      return unwrap<T>(m, path, raw);
    } catch (e) {
      lastError = e instanceof ApiError ? e : networkError(e);
      // Ретраим только network/5xx; 401/403/4xx — сразу наверх
      const retryable = lastError.code === 'NETWORK' || (lastError.status >= 500 && lastError.status < 600);
      if (i === attempts || !retryable) throw lastError;
    }
  }
  throw lastError!;
}

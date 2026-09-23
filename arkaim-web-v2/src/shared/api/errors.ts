/**
 * errors.ts — единая модель ошибок API (F1_SPEC §7).
 *
 * Backend отдаёт ДВА формата (forensic §2.2):
 *   1. Глобальный handler:  {"ok": false, "error": {"code": "...", "message": "..."}}
 *   2. HTTPException (FastAPI): {"detail": "..."}
 * Оба парсятся в единый ApiError. Frontend никогда не работает с сырыми телами.
 */

export type ApiErrorCode =
  | `HTTP_${number}`
  | 'NETWORK'
  | 'TIMEOUT'
  | 'PARSE'
  | 'UNKNOWN';

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly details?: unknown;
  readonly isAuthError: boolean;
  readonly isForbidden: boolean;

  constructor(status: number, code: ApiErrorCode, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.isAuthError = status === 401;
    this.isForbidden = status === 403;
  }
}

/** Разобрать тело ошибки backend'а в ApiError. */
export function parseErrorBody(status: number, body: unknown): ApiError {
  if (body && typeof body === 'object') {
    const b = body as Record<string, unknown>;

    // Формат 1: {ok:false, error:{code,message,details?}}
    if (b.error && typeof b.error === 'object') {
      const e = b.error as Record<string, unknown>;
      const code = typeof e.code === 'string' ? e.code : `HTTP_${status}`;
      const message = typeof e.message === 'string' ? e.message : `Ошибка HTTP ${status}`;
      return new ApiError(status, code as ApiErrorCode, message, e.details);
    }

    // Формат 2: {detail: "..."} (FastAPI HTTPException)
    if (typeof b.detail === 'string') {
      return new ApiError(status, `HTTP_${status}`, b.detail);
    }
    // Pydantic validation: {detail: [{loc, msg, type}...]}
    if (Array.isArray(b.detail)) {
      const first = b.detail[0] as Record<string, unknown> | undefined;
      const msg = first?.msg ? String(first.msg) : 'Ошибка валидации';
      return new ApiError(status, `HTTP_${status}`, msg, b.detail);
    }
  }
  return new ApiError(status, `HTTP_${status}`, `Ошибка HTTP ${status}`, body);
}

export function networkError(cause?: unknown): ApiError {
  return new ApiError(0, 'NETWORK', 'Нет соединения с сервером', cause);
}

export function timeoutError(): ApiError {
  return new ApiError(0, 'TIMEOUT', 'Превышено время ожидания');
}

export function parseError(cause?: unknown): ApiError {
  return new ApiError(0, 'PARSE', 'Некорректный ответ сервера', cause);
}

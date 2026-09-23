/**
 * contracts/auth.ts — typed-контракты аутентификации (F1_SPEC §5).
 *
 * Auth-ответы backend не имеют response_model → в OpenAPI-схемах пустые,
 * поэтому типы фиксируются ЗДЕСЬ по ФАКТИЧЕСКОМУ JSON (forensic §2.3, auth/routes.py):
 *   /auth/me      → {user: {id, role, username?, display_name?, provider}}
 *   /auth/register→ {ok, user: {...}} + Set-Cookie arkaim_session
 *   /auth/telegram/login|callback → {ok, user: {...}} + Set-Cookie
 *   /auth/dev/generate-token → {token, login_url}
 * Роли: reader | editor | admin (ROLE_HIERARCHY backend).
 */

import { apiCall } from '../client';

export type Role = 'reader' | 'editor' | 'admin';

export interface AuthUser {
  id: string;
  role: Role;
  username?: string | null;
  display_name?: string | null;
  provider?: string | null;
}

/** GET /auth/me — 401 без сессии; {user} с сессией. */
export async function getMe(): Promise<AuthUser | null> {
  try {
    const body = await apiCall<{ user?: AuthUser }>('GET', '/auth/me');
    return body?.user ?? null;
  } catch (e) {
    const err = e as { status?: number };
    if (err?.status === 401) return null;
    throw e;
  }
}

export interface RegisterRequest {
  username: string;
  display_name?: string;
}

/** POST /auth/register — создаёт reader, ставит cookie. */
export function register(req: RegisterRequest): Promise<{ ok: boolean; user: AuthUser }> {
  return apiCall('POST', '/auth/register', { method: 'POST', body: req });
}

/** POST /auth/telegram/login — вход по токену Telegram-виджета. */
export function telegramLogin(token: string): Promise<{ ok: boolean; user: AuthUser }> {
  return apiCall('POST', '/auth/telegram/login', { method: 'POST', body: { token } });
}

/** POST /auth/telegram/callback — данные Telegram-виджета. */
export function telegramCallback(data: Record<string, unknown>): Promise<{ ok: boolean; user: AuthUser }> {
  return apiCall('POST', '/auth/telegram/callback', { method: 'POST', body: data });
}

/**
 * POST /auth/dev/generate-token — ТОЛЬКО dev-режим (NEXT_PUBLIC_DEV_AUTH=1).
 * Вызывающий слой обязан проверять флаг ДО вызова (см. useDevAuth).
 */
export interface DevTokenResponse {
  token: string;
  login_url: string;
}

export function devGenerateToken(username: string, role?: Role): Promise<DevTokenResponse> {
  return apiCall('POST', '/auth/dev/generate-token', {
    method: 'POST',
    body: {
      telegram_user_id: `dev-${username}`,
      username,
      display_name: username,
      role: role ?? 'admin',
    },
  });
}

/**
 * POST /auth/logout — просит браузер удалить cookie arkaim_session.
 * Backend — stateless JWT: сам токен остаётся валиден до истечения (12ч);
 * это контрактная особенность backend (F1-аудит §5), не дефект фронтенда.
 */
export function logout(): Promise<unknown> {
  return apiCall('POST', '/auth/logout', { method: 'POST' });
}

/** GET /health — системный статус (foundation-дашборд). */
export interface HealthResponse {
  status: string;
  mode?: string;
  active_traces?: number;
  completed_traces?: number;
}

export function getHealth(): Promise<HealthResponse> {
  return apiCall('GET', '/health');
}

// ── Admin endpoints (admin-only) ──────────────────────────
// Все ответы backend — raw JSON (не enveloped {ok, data}).
// Проверялось live: POST role/toggle/delete и GET list/stats возвращают прямой JSON.

export interface AdminUser {
  id: string;
  provider: string;
  provider_user_id: string;
  username: string;
  display_name: string;
  role: Role;
  is_active: number;
  created_at: string;
  updated_at?: string;
}

export interface AdminStats {
  users: {
    total: number;
    by_role: Record<string, number>;
  };
  reader_memory: Record<string, unknown>;
  presence: {
    trending_topics: number;
    pending_suggestions: number;
  };
  email: {
    subscribers: number;
    drafts: number;
  };
}

export interface AdminApiKey {
  id: string;
  user_id: string;
  key_prefix: string;
  name: string | null;
  last_used_at: string | null;
  is_active: number;
  created_at: string;
}

/** GET /auth/admin/users — список всех пользователей. */
export function getAdminUsers(): Promise<AdminUser[]> {
  return apiCall('GET', '/auth/admin/users');
}

/** GET /auth/admin/users/{id} — детали пользователя. */
export function getAdminUser(id: string): Promise<AdminUser> {
  return apiCall('GET', `/auth/admin/users/${id}`);
}

/**
 * POST /auth/admin/users/{id}/role — смена роли.
 * body: { role: 'reader' | 'editor' | 'admin' }.
 * response: { ok: true, user_id, role }.
 */
export function updateUserRole(
  userId: string,
  role: Role,
): Promise<{ ok: boolean; user_id: string; role: Role }> {
  return apiCall('POST', `/auth/admin/users/${userId}/role`, {
    method: 'POST',
    body: { role },
  });
}

/**
 * POST /auth/admin/users/{id}/toggle — активация/деактивация.
 * response: { ok: true, user_id }.
 */
export function toggleUser(userId: string): Promise<{ ok: boolean; user_id: string }> {
  return apiCall('POST', `/auth/admin/users/${userId}/toggle`, {
    method: 'POST',
    body: {},
  });
}

/** DELETE /auth/admin/users/{id} — удалить пользователя. */
export function deleteUser(userId: string): Promise<{ ok: boolean; user_id: string }> {
  return apiCall('DELETE', `/auth/admin/users/${userId}`);
}

/** GET /auth/admin/stats — сводная статистика. */
export function getAdminStats(): Promise<AdminStats> {
  return apiCall('GET', '/auth/admin/stats');
}

/** GET /auth/admin/api-keys — ключи всех пользователей. */
export function getAdminApiKeys(): Promise<AdminApiKey[]> {
  return apiCall('GET', '/auth/admin/api-keys');
}

/** DELETE /auth/admin/api-keys/{id} — удалить ключ. */
export function deleteAdminApiKey(keyId: string): Promise<{ ok: boolean; key_id: string }> {
  return apiCall('DELETE', `/auth/admin/api-keys/${keyId}`);
}

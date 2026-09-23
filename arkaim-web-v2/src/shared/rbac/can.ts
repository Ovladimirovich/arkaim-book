/**
 * rbac/can.ts — доступ по фактической матрице backend (F1_SPEC §8).
 *
 * Матрица порождается из committed-слепка contracts/rbac-matrix.json
 * (307 маршрутов; сгенерировано scripts/contracts.mjs — не править руками).
 *
 * can(user, path, method) — единственная точка принятия решений UI.
 * Правило backend (auth/rbac.py require_role): роль >= min(allowed_levels),
 * где reader=0, editor=1, admin=2. Пустые roles = маршрут публичный.
 * НО: часть «публичных» маршрутов проверяет аутентификацию ВНУТРИ тела
 * (forensic §2.4) — для UI-видимости используем консервативную политику
 * доступа UI_NAV (см. ниже): навигация показывается только по
 * зафиксированным ролевым группам.
 */

import { RBAC_MATRIX } from './generated/matrix';
import type { Role } from '@/shared/api/contracts/auth';

const LEVEL: Record<Role, number> = { reader: 0, editor: 1, admin: 2 };

/** Известные backend-дефекты (forensic §2.7) — НЕ вызывать/НЕ показывать. */
export const BACKEND_DEFECTS: Record<string, string> = {
  '/book/book/crowdfunding/{campaign_id}': 'D1: дублирующее монтирование /book/book/* — не использовать',
  '/book/research-engine/apply/{job_id}': 'D2: заглушка, ничего не применяет — не обещать в UI',
};

/** Иерархия ролей backend (ROLE_HIERARCHY, auth/rbac.py). */
export function roleLevel(role: Role): number {
  return LEVEL[role];
}

/**
 * Может ли пользователь вызвать endpoint (по матрице).
 * routeRoles пуст → маршрут публичный (вызывать можно всем).
 * Иначе: уровень роли пользователя >= min(уровней разрешённых).
 */
export function can(role: Role, path: string, method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' = 'GET'): boolean {
  const m = method.toUpperCase();
  const entry = RBAC_MATRIX.find((r) => r.path === path && r.methods.includes(m as never));
  if (!entry) return false; // неизвестный маршрут — нельзя (контракт-гейт)
  if (entry.roles.length === 0) return true; // public
  const minAllowed = Math.min(...entry.roles.map((r) => LEVEL[r as Role] ?? 99));
  return LEVEL[role] >= minAllowed;
}

/** Есть ли у пользователя хотя бы одна роль из списка. */
export function hasAnyRole(role: Role, allowed: readonly Role[]): boolean {
  return allowed.includes(role);
}

/** Минимальная роль, необходимая для маршрута (для отображения замков). */
export function minRoleFor(path: string, method = 'GET'): Role | 'public' | 'unknown' {
  const entry = RBAC_MATRIX.find((r) => r.path === path && r.methods.includes(method as never));
  if (!entry) return 'unknown';
  if (entry.roles.length === 0) return 'public';
  const minLevel = Math.min(...entry.roles.map((r) => LEVEL[r as Role] ?? 99));
  return (Object.keys(LEVEL) as Role[]).find((r) => LEVEL[r] === minLevel) ?? 'unknown';
}

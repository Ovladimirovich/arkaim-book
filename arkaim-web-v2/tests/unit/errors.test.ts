/**
 * errors.test.ts — единая ApiError-модель: оба формата backend (F1_SPEC §7).
 */
import { describe, expect, it } from 'vitest';
import { parseErrorBody, ApiError } from '@/shared/api/errors';

describe('parseErrorBody', () => {
  it('Формат 1: {ok:false, error:{code,message}} — глобальный handler', () => {
    const e = parseErrorBody(409, { ok: false, error: { code: 'HTTP_409', message: 'Конфликт' } });
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(409);
    expect(e.code).toBe('HTTP_409');
    expect(e.message).toBe('Конфликт');
  });

  it('Формат 2: {detail: "..."} — FastAPI HTTPException', () => {
    const e = parseErrorBody(401, { detail: 'Не авторизован' });
    expect(e.status).toBe(401);
    expect(e.code).toBe('HTTP_401');
    expect(e.message).toBe('Не авторизован');
    expect(e.isAuthError).toBe(true);
  });

  it('Формат 2b: {detail: [...]} — pydantic-валидация', () => {
    const e = parseErrorBody(422, { detail: [{ loc: ['body'], msg: 'обязательное поле', type: 'missing' }] });
    expect(e.code).toBe('HTTP_422');
    expect(e.message).toBe('обязательное поле');
  });

  it('403 → isForbidden', () => {
    const e = parseErrorBody(403, { detail: 'Недостаточно прав' });
    expect(e.isForbidden).toBe(true);
  });

  it('Неизвестное тело → UNKNOWN-фолбэк', () => {
    const e = parseErrorBody(500, 'сырой текст');
    expect(e.code).toBe('HTTP_500');
  });
});

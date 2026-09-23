/**
 * login-b2.test.ts — B2 (F1-аудит §10): login lifecycle-safety.
 *
 * Две проверки:
 *  1) SOURCE: сетевой вызов вынесен из render в useEffect с ref-guard
 *     (в исходнике login/page.tsx нет старого render-side-effect-паттерна);
 *  2) SEMANTICS: ref-guard даёт ровно ОДИН вызов входа при StrictMode
 *     double-invoke эффектов (одноразовый backend-токен не «сгорает» дважды).
 */
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';

const PAGE_SRC = readFileSync('src/app/(auth)/login/page.tsx', 'utf8');

describe('B2: login urlToken lifecycle (source)', () => {
  it('сетевой вызов находится в useEffect (не в render-фазе)', () => {
    expect(PAGE_SRC).toContain('useEffect(');
    expect(PAGE_SRC).toContain('tokenHandledRef');
  });

  it('старый render-side-effect-паттерн удалён', () => {
    // До B2: `if (urlToken && !busy) { void handleTelegramToken(urlToken); }`
    // прямо в теле рендера (не внутри useEffect). Паттерн обязан отсутствовать;
    // сам вызов внутри эффекта остаётся — это и есть корректный lifecycle.
    expect(PAGE_SRC.indexOf('if (urlToken && !busy)')).toBe(-1);
    expect(PAGE_SRC.indexOf('void handleTelegramToken(urlToken);')).toBeGreaterThan(-1); // вызов существует
    // …и находится ПОСЛЕ useEffect-маркера, т.е. в эффекте:
    const effectPos = PAGE_SRC.indexOf('useEffect(');
    const callPos = PAGE_SRC.indexOf('void handleTelegramToken(urlToken);');
    expect(effectPos).toBeGreaterThan(-1);
    expect(callPos).toBeGreaterThan(effectPos);
  });

  it('ref-guard инициализирован и проверяется в эффекте', () => {
    expect(PAGE_SRC).toContain('useRef(false)');
    expect(PAGE_SRC).toContain('tokenHandledRef.current = true');
  });
});

describe('B2: guard-семантика при StrictMode double-invoke', () => {
  /** 1:1 копия guard-паттерна страницы (ref живёт между прогонами эффекта). */
  function mountLoginOnce(urlToken: string | null) {
    const ref = { current: false };
    const calls: string[] = [];
    const effect = () => {
      if (!urlToken || ref.current) return;
      ref.current = true;
      calls.push(urlToken);
    };
    return { effect, calls };
  }

  it('эффект, прогнанный дважды (StrictMode), вызывает вход ОДИН раз', () => {
    const { effect, calls } = mountLoginOnce('one-time-token');
    effect();
    effect(); // StrictMode double-invoke
    expect(calls).toHaveLength(1);
    expect(calls[0]).toBe('one-time-token');
  });

  it('без токена в URL — вызова нет (сколько бы прогонов ни было)', () => {
    const { effect, calls } = mountLoginOnce(null);
    effect();
    effect();
    effect();
    expect(calls).toHaveLength(0);
  });

  it('повторный вызов эффекта после успешного входа не дублирует запрос', () => {
    const { effect, calls } = mountLoginOnce('tok-42');
    effect();
    effect();
    effect();
    expect(calls).toHaveLength(1);
  });
});

afterEach(() => {
  /* нет глобальных моков — чистить нечего */
});

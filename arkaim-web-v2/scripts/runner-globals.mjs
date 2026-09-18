/**
 * runner-globals.mjs — реализация describe/it/expect/vi для sandbox-раннера.
 * Вынос в модуль, чтобы vitest-shim мог реэкспортировать те же объекты,
 * что run-tests.mjs устанавливает в globals (единый реестр).
 */
const state = { passed: 0, failed: 0, failures: [] };

// ── Тесты накапливаются на фазе загрузки, исполняются на фазе run ──
const testQueue = [];
const stack = [];
export function describe(name, fn) {
  stack.push(name);
  try { fn(); } finally { stack.pop(); }
}
export function it(name, fn) {
  testQueue.push({ name: [...stack, name].join(' › '), fn, hooks: activeHooks });
}

// ── beforeEach/afterEach: per-module (коллекция активна пока грузится файл) ──
let activeHooks = { before: [], after: [] };
export function beforeEach(fn) { activeHooks.before.push(fn); }
export function afterEach(fn) { activeHooks.after.push(fn); }
/** run-tests.mjs открывает/закрывает контекст файла (сброс hooks). */
export function beginModule() { activeHooks = { before: [], after: [] }; }
export function endModule() { activeHooks = { before: [], after: [] }; }

/** Исполнить накопленные тесты (вызывается run-tests.mjs после загрузки всех модулей). */
export async function runAll() {
  for (const t of testQueue) {
    try {
      for (const f of [...t.hooks.before]) await f();
      try {
        await t.fn();
      } finally {
        for (const f of [...t.hooks.after]) await f();
      }
      state.passed++;
      console.log(`  ✓ ${t.name}`);
    } catch (e) {
      state.failed++;
      state.failures.push({ name: t.name, error: e });
      console.error(`  ✗ ${t.name}\n      ${e?.message}`);
    }
  }
}

/** Очистить очередь после прогона модуля (per-module изоляция, как в vitest per-file). */
export function clearTests() {
  testQueue.length = 0;
}

// ── expect ──
function deepEq(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function assertObj(actual) {
  const matchers = {
    toBe(exp) { if (actual !== exp) throw new Error(`expected ${JSON.stringify(exp)}, got ${JSON.stringify(actual)}`); },
    toEqual(exp) { if (!deepEq(actual, exp)) throw new Error(`expected deep ${JSON.stringify(exp)}, got ${JSON.stringify(actual)}`); },
    toBeTruthy() { if (!actual) throw new Error(`expected truthy, got ${JSON.stringify(actual)}`); },
    toBeNull() { if (actual !== null) throw new Error(`expected null, got ${JSON.stringify(actual)}`); },
    toBeDefined() { if (actual === undefined) throw new Error('expected defined'); },
    toBeInstanceOf(cls) { if (!(actual instanceof cls)) throw new Error(`expected instance of ${cls.name}`); },
    toContain(sub) {
      if (Array.isArray(actual)) { if (!actual.includes(sub)) throw new Error(`expected array to contain ${JSON.stringify(sub)}`); }
      else if (!String(actual).includes(sub)) throw new Error(`expected to contain "${sub}"`);
    },
    toHaveLength(n) { if (!actual || actual.length !== n) throw new Error(`expected length ${n}, got ${actual?.length}`); },
    toBeGreaterThan(n) { if (!(actual > n)) throw new Error(`expected > ${n}, got ${actual}`); },
    toBeGreaterThanOrEqual(n) { if (!(actual >= n)) throw new Error(`expected >= ${n}, got ${actual}`); },
    toMatchObject(obj) {
      for (const [k, v] of Object.entries(obj)) {
        const a = actual?.[k];
        if (typeof v === 'object' && v !== null) {
          for (const [k2, v2] of Object.entries(v)) {
            if (JSON.stringify(a?.[k2]) !== JSON.stringify(v2)) throw new Error(`expected ${k}.${k2}=${JSON.stringify(v2)}, got ${JSON.stringify(a?.[k2])}`);
          }
        } else if (a !== v) throw new Error(`expected ${k}=${JSON.stringify(v)}, got ${JSON.stringify(a)}`);
      }
    },
  };
  const notObj = {};
  for (const [k, v] of Object.entries(matchers)) {
    notObj[k] = async (...args) => {
      try { await v(...args); } catch { return; }
      throw new Error(`NOT-мatcher ${k}: ожидалось падение, прошло (${JSON.stringify(actual)})`);
    };
  }
  matchers.not = notObj;
  matchers.rejects = {
    async toMatchObject(obj) {
      try { await actual; throw new Error('expected rejection'); }
      catch (e) { if (e.message === 'expected rejection') throw e; assertObj(e).toMatchObject(obj); }
    },
    async toThrow(msg) {
      try { await actual; throw new Error('expected rejection'); }
      catch (e) { if (e.message === 'expected rejection') throw e; if (msg && !String(e).includes(msg)) throw new Error(`expected error to contain "${msg}", got "${e}"`); }
    },
  };
  return matchers;
}
export function expect(actual) { return assertObj(actual); }

// ── vi ──
export function makeVi() {
  const savedGlobals = new Map();
  let fakeTimers = null; // { now, queue: Map<id, {at, fn, args}> }

  function fn(impl) {
    const f = (...args) => {
      f.mock.calls.push(args);
      if (f.mock.impl) return f.mock.impl(...args);
      return f.mock.defaultImpl ? f.mock.defaultImpl(...args) : undefined;
    };
    f.mockReset = () => { f.mock.calls.length = 0; f.mock.impl = impl ?? null; f.mock.defaultImpl = null; };
    f.mock = {
      calls: [],
      impl: impl ?? null,
      defaultImpl: null,
      reset() { f.mockReset(); },
      mockReset() { f.mockReset(); },
      mockResolvedValue(v) { f.mock.defaultImpl = () => Promise.resolve(v); },
      mockRejectedValue(v) { f.mock.defaultImpl = () => Promise.reject(v); },
    };
    // vitest-совместимые top-level алиасы
    f.mockReset = f.mockReset;
    f.mockClear = f.mockReset;
    f.mockResolvedValue = (v) => f.mock.mockResolvedValue(v);
    f.mockRejectedValue = (v) => f.mock.mockRejectedValue(v);
    f.mockImplementation = (i) => { f.mock.impl = i; };
    return f;
  }

  return {
    fn,
    stubGlobal(name, value) {
      if (!savedGlobals.has(name)) savedGlobals.set(name, globalThis[name]);
      globalThis[name] = value;
    },
    restoreAllMocks() {
      for (const [name, value] of savedGlobals) {
        if (value === undefined) delete globalThis[name];
        else globalThis[name] = value;
      }
      savedGlobals.clear();
    },
    useFakeTimers() {
      fakeTimers = {
        queue: new Map(),
        nextId: 1,
        realSetTimeout: globalThis.setTimeout,
        realClearTimeout: globalThis.clearTimeout,
      };
      globalThis.__vitestFakeTimers = fakeTimers;
      // Перехват setTimeout/clearTimeout глобально (для WsClient reconnect)
      globalThis.setTimeout = (fn, delay = 0, ...args) => {
        const id = fakeTimers.nextId++;
        fakeTimers.queue.set(id, { at: Date.now() + delay, fn, args });
        return id;
      };
      globalThis.clearTimeout = (id) => { fakeTimers.queue.delete(id); };
    },
    useRealTimers() {
      if (fakeTimers) {
        globalThis.setTimeout = fakeTimers.realSetTimeout;
        globalThis.clearTimeout = fakeTimers.realClearTimeout;
      }
      globalThis.__vitestFakeTimers = null;
      fakeTimers = null;
    },
    advanceTimersByTime(ms) {
      const ft = globalThis.__vitestFakeTimers;
      if (!ft) return;
      // Исполнить все таймеры с дедлайном <= now+ms (могут ставить новые — цикл)
      let elapsed = 0;
      while (elapsed <= ms) {
        const next = [...ft.queue.values()].sort((a, b) => a.at - b.at)[0];
        if (!next || next.at - Date.now() > ms - elapsed) break;
        ft.queue.delete([...ft.queue.entries()].find(([, t]) => t === next)?.[0]);
        next.fn(...next.args);
        elapsed = ms; // после первого исполненного тика считаем «время прошло»
      }
    },
  };
}

export { state };

/**
 * vitest-shim.mjs — локальная замена 'vitest' для sandbox-раннера.
 * Реэкспортирует describe/it/expect/vi из runner-globals (единый реестр),
 * поэтому 'import { describe, it } from "vitest"' работает в тест-файлах.
 * (Настоящий vitest под sandbox не стартует: spawn EPERM; CI использует штатный.)
 */
import { describe, it, expect, makeVi, beforeEach, afterEach } from './runner-globals.mjs';

export { describe, it, expect, beforeEach, afterEach };
export const vi = makeVi();


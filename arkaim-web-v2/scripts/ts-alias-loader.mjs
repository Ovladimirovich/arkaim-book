/**
 * ts-alias-loader.mjs — resolve-хук для node native TS (sandbox-раннер):
 *   '@/x'      → '<root>/src/x'
 *   './x'      → рядом с importer: x.ts / x/index.ts (node не делает ext-resolve TS)
 *   'vitest'   → scripts/vitest-shim.mjs (в in-process режиме настоящий vitest
 *                стартовать нельзя — spawn EPERM)
 *   '*.json'   → из <root> с import-атрибутом {type:'json'}
 * Только для scripts/run-tests.mjs; vitest/CI резолвит всё штатно.
 */
import { pathToFileURL } from 'node:url';
import path from 'node:path';
import { existsSync } from 'node:fs';

function winPathFromUrl(u) {
  return decodeURIComponent(new URL(u).pathname.replace(/^\/([A-Za-z]:)/i, '$1'));
}

export async function resolve(specifier, context, nextResolve) {
  // 'vitest' → shim (тот же набор describe/it/expect/vi, что в globals)
  if (specifier === 'vitest') {
    const shimPath = path.resolve(winPathFromUrl(import.meta.url), '..', 'vitest-shim.mjs');
    return { url: pathToFileURL(shimPath).href, shortCircuit: true };
  }

  // '@/'-алиас
  if (specifier.startsWith('@/')) {
    const base = path.join(winPathFromUrl(import.meta.url), '..', '..', 'src', specifier.slice(2));
    return tryTs(base, context, nextResolve);
  }

  // Относительный TS-импорт без расширения → добавить .ts/.tsx/index.ts
  if ((specifier.startsWith('./') || specifier.startsWith('../')) && !/\.(mjs|cjs|json)$/.test(specifier)) {
    const importerDir = path.dirname(winPathFromUrl(context.parentURL ?? import.meta.url));
    const base = path.resolve(importerDir, specifier);
    return tryTs(base, context, nextResolve);
  }

  // JSON-импорт (любой относительный/абсолютный путь) — node native
  // требует import-атрибут {type:'json'}; подставляем его прозрачно
  if (specifier.endsWith('.json')) {
    let abs;
    if (specifier.startsWith('@/')) {
      abs = path.join(winPathFromUrl(import.meta.url), '..', '..', 'src', specifier.slice(2));
    } else if (specifier.startsWith('./') || specifier.startsWith('../')) {
      const importerDir = path.dirname(winPathFromUrl(context.parentURL ?? import.meta.url));
      abs = path.resolve(importerDir, specifier);
    } else if (specifier.startsWith('/')) {
      abs = path.join(winPathFromUrl(import.meta.url), '..', '..', specifier);
    } else {
      return nextResolve(specifier, context);
    }
    return nextResolve(pathToFileURL(abs).href, { ...context, importAttributes: { type: 'json' } });
  }

  return nextResolve(specifier, context);
}

async function tryTs(base, context, nextResolve) {
  const candidates = [
    base,
    `${base}.ts`,
    `${base}.tsx`,
    `${base}/index.ts`,
    `${base}/index.tsx`,
  ];
  // Сначала точное существование файла (node кинет ENOENT если нет)
  for (const c of candidates) {
    if (existsSync(c) && path.extname(c) !== '') {
      return nextResolve(pathToFileURL(c).href, context);
    }
  }
  return nextResolve(pathToFileURL(`${base}.ts`).href, context);
}

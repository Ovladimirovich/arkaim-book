/**
 * contracts.test.ts — CI-гейт целостности контрактов (F1_SPEC §10, §11).
 * Связывает committed-слепки ↔ generated-артефакты ↔ ручные typed-контракты.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { ENVELOPE_MAP } from '@/shared/api/envelope';
import { RBAC_MATRIX, RBAC_ROUTES_TOTAL } from '@/shared/rbac/generated/matrix';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '../..');
const openapi = JSON.parse(
  readFileSync(resolve(ROOT, 'contracts/openapi.json'), 'utf8'),
) as { paths: Record<string, Record<string, unknown>> };
const rbacSnapshot = JSON.parse(
  readFileSync(resolve(ROOT, 'contracts/rbac-matrix.json'), 'utf8'),
) as { total_routes: number; routes: { path: string; methods: string[]; roles: string[] }[] };

describe('openapi snapshot ↔ generated schema', () => {
  it('слепок: 290 путей', () => {
    expect(Object.keys(openapi.paths)).toHaveLength(290);
  });

  it('schema.d.ts существует и не пуст', () => {
    const schema = readFileSync(resolve(ROOT, 'src/shared/api/generated/schema.d.ts'), 'utf8');
    expect(schema.length).toBeGreaterThan(100_000);
    expect(schema).toContain('paths');
  });

  it('envelope-карта покрывает только реально существующие пути', () => {
    for (const key of Object.keys(ENVELOPE_MAP)) {
      const [, path] = key.split(' ');
      expect(openapi.paths[path], `ENVELOPE_MAP содержит несуществующий путь ${path}`).toBeDefined();
    }
  });

  it('F5: xray endpoints в envelope map', () => {
    expect(ENVELOPE_MAP['GET /xray/events/stream']).toBe('direct');
    expect(ENVELOPE_MAP['GET /xray/stats']).toBe('direct');
    expect(ENVELOPE_MAP['GET /xray/events']).toBe('direct');
    expect(ENVELOPE_MAP['GET /xray/version']).toBe('direct');
  });

  it('F5: history endpoints в envelope map', () => {
    expect(ENVELOPE_MAP['GET /book/reader/history/sessions']).toBe('enveloped');
    expect(ENVELOPE_MAP['GET /book/reader/history/full']).toBe('enveloped');
  });
});

describe('rbac snapshot ↔ generated matrix', () => {
  it('matrix.ts == слепку (json)', () => {
    expect(RBAC_ROUTES_TOTAL).toBe(rbacSnapshot.total_routes);
    expect(RBAC_MATRIX).toHaveLength(rbacSnapshot.routes.length);
    for (let i = 0; i < rbacSnapshot.routes.length; i++) {
      expect(RBAC_MATRIX[i].path).toBe(rbacSnapshot.routes[i].path);
      expect(RBAC_MATRIX[i].roles).toEqual(rbacSnapshot.routes[i].roles);
    }
  });

  it('навигация ссылается только на существующие backend-контракты', async () => {
    const { NAV_GROUPS } = await import('@/shared/rbac/navigation');
    for (const g of NAV_GROUPS) {
      for (const item of g.items) {
        if (!item.contractPath) continue;
        const [method, path] = item.contractPath.split(' ');
        const ops = openapi.paths[path];
        expect(ops, `Nav "${item.label}": путь ${path} отсутствует в OpenAPI`).toBeDefined();
        expect(ops[method.toLowerCase()], `Nav "${item.label}": метод ${method} отсутствует`).toBeDefined();
      }
    }
  });
});

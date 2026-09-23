/**
 * world.test.ts — world-контракты против mock-транспорта (F2_SPEC §7).
 * Live-факт: ответы direct (без enveloped-ok обёртки).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

import {
  getWorldSummary,
  getWorldCategories,
  searchWorld,
  getWorldEntity,
  getWorldRules,
  getWorldModes,
} from '@/shared/api/contracts/world';

afterEach(() => {
  fetchMock.mockReset();
});

describe('GET /book/world/summary', () => {
  it('direct → {summary, stats}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          summary: 'World Engine: обнаружено 547 сущностей',
          stats: { world_model: { total_categories: 13, total_entities: 547, by_category: { philosophy: 268 } } },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getWorldSummary();
    expect(r.summary).toContain('547');
    expect(r.stats.world_model.total_entities).toBe(547);
    expect(r.stats.world_model.total_categories).toBe(13);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/world/summary');
  });
});

describe('GET /book/world/categories', () => {
  it('direct → {categories, total}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          categories: { philosophy: 268, language: 134, geography: 38 },
          total: 13,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getWorldCategories();
    expect(r.categories.philosophy).toBe(268);
    expect(r.total).toBe(13);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/world/categories');
  });
});

describe('POST /book/world/search', () => {
  it('direct → {world_model, relations, total}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          world_model: [
            { id: 'arkaim_settlement', name: 'Аркаим', category: 'architecture', description: 'Древнее поселение' },
            { id: 'geo_arkaim_river', name: 'Река у Аркаима', category: 'geography', description: 'Река' },
          ],
          relations: [],
          total: 2,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await searchWorld({ query: 'Аркаим', limit: 5 });
    expect(r.world_model).toHaveLength(2);
    expect(r.world_model[0].id).toBe('arkaim_settlement');
    expect(r.total).toBe(2);
    expect(fetchMock.mock.calls[0][0]).toBe('/book/world/search');
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).query).toBe('Аркаим');
  });
});

describe('GET /book/world/entity/{id}', () => {
  it('direct → {category, id, name, description, properties}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          category: 'architecture',
          id: 'arkaim_settlement',
          name: 'Аркаим',
          name_ru: 'Аркаим',
          description: 'Древнее круглое поселение',
          properties: { type: 'ancient_settlement', style: 'circular_fortified' },
          relations: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getWorldEntity('arkaim_settlement');
    expect(r.id).toBe('arkaim_settlement');
    expect(r.category).toBe('architecture');
    expect(r.properties?.type).toBe('ancient_settlement');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/world/entity/arkaim_settlement');
  });
});

describe('GET /book/world/rules', () => {
  it('direct → {rules: [{id, name_ru, severity}]}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          rules: [
            { id: 'temporal_no_future', name: 'No Future Knowledge', name_ru: 'Без знания будущего', rule_type: 'temporal', severity: 'hard' },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getWorldRules();
    expect(r.rules).toHaveLength(1);
    expect(r.rules[0].severity).toBe('hard');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/world/rules');
  });
});

describe('GET /book/world/modes', () => {
  it('direct → {modes: [{mode, name_ru, description_ru}]}', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          modes: [
            { mode: 'dialog', name: 'Диалог', name_ru: 'Диалог', description: 'Режим диалога' },
            { mode: 'story', name: 'Сюжет', name_ru: 'Сюжет', description: 'Режим сюжета' },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getWorldModes();
    expect(r.modes).toHaveLength(2);
    expect(r.modes[0].mode).toBe('dialog');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/world/modes');
  });
});

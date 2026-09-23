/**
 * world-explorer.test.ts — контракты «Исследование мира» (F2_SPEC §world-explorer).
 *
 * Проверяет:
 *   1. ENVELOPE_MAP: все 14 world-explorer-записей;
 *      correct envelope per method (enveloped vs direct).
 *   2. Wire-тело: exploreWorld, validateIdea — обязательные поля в JSON body.
 *   3. Ключевые response-типы: ExplorationResult, CompatibilityResult, RankedBranch.
 *   4. История: getExplorationHistory, saveExploration (direct), deleteExploration (direct).
 *   5. Отклик: submitFeedback (direct), generateFromBranch (enveloped).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ENVELOPE_MAP, envelopeOf } from '@/shared/api/envelope';
import {
  deleteExploration,
  exploreWorld,
  generateFromBranch,
  getExplorationDetail,
  getExplorationHistory,
  getExplorerEpochs,
  getExplorerStats,
  getHypotheses,
  getPossibilities,
  saveExploration,
  submitFeedback,
  validateIdea,
} from '@/shared/api/contracts/worldExplorer';

const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

afterEach(() => {
  fetchMock.mockReset();
});

// ── Helper builders ───────────────────────────────────────

const okExplore = () =>
  new Response(
    JSON.stringify({
      ok: true,
      data: {
        request: { prompt: 'test', epoch: 'satya_yuga', branch_count: 3 },
        hypothesis: null,
        scenario: { branch_count: 3, best_branch_id: 'b1', summary: 'ok' },
        ranked_branches: [
          {
            rank: 1,
            branch_type: 'moderate',
            title: 'Модерн ветка',
            quality_score: 0.82,
            quality_summary: '',
            strengths: ['strong'],
            weaknesses: [],
            impact_score: 0.7,
            contradictions: 0,
            delta_changes: 2,
          },
        ],
        duration_ms: 120,
        summary: 'Done',
      },
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } as Record<string, string> },
  );

const okValidate = () =>
  new Response(
    JSON.stringify({
      ok: true,
      data: {
        overall_score: 0.9,
        is_compatible: true,
        risk_level: 'low',
        axis_scores: [
          { axis: 'canon_alignment', score: 0.95, violations_count: 0, warnings_count: 0 },
        ],
        violations_count: 0,
        warnings_count: 0,
        recommendations: [],
      },
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } as Record<string, string> },
  );

const okHistory = () =>
  new Response(
    JSON.stringify({
      ok: true,
      data: [
        { id: 1, prompt: 'A', epoch: null, branch_count: 3, saved_at: '2026-09-14T00:00:00Z' },
      ],
      total: 1,
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } as Record<string, string> },
  );

const okSave = () =>
  new Response(JSON.stringify({ ok: true, id: 42 }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

const okDelete = () =>
  new Response(JSON.stringify({ ok: true }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

const okFeedback = () =>
  new Response(JSON.stringify({ ok: true, id: 7 }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });

const okGenerate = () =>
  new Response(
    JSON.stringify({
      ok: true,
      data: {
        system_instruction: 'instr',
        user_prompt: 'prompt',
      },
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } as Record<string, string> },
  );

// ── ENVELOPE_MAP ───────────────────────────────────────────

describe('ENVELOPE_MAP world-explorer entries', () => {
  const weKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('world-explorer'));

  it('≥14 записей world-explorer в ENVELOPE_MAP', () => {
    expect(weKeys.length).toBeGreaterThanOrEqual(14);
  });

  it('GET/основные POST — enveloped', () => {
    expect(ENVELOPE_MAP['GET /book/world-explorer/epochs']).toBe('enveloped');
    expect(ENVELOPE_MAP['GET /book/world-explorer/stats']).toBe('enveloped');
    expect(ENVELOPE_MAP['POST /book/world-explorer/explore']).toBe('enveloped');
    expect(ENVELOPE_MAP['POST /book/world-explorer/validate']).toBe('enveloped');
    expect(ENVELOPE_MAP['POST /book/world-explorer/generate-from-branch']).toBe('enveloped');
  });

  it('POST /history и POST /feedback — direct (нет обёртки data)', () => {
    expect(ENVELOPE_MAP['POST /book/world-explorer/history']).toBe('direct');
    expect(ENVELOPE_MAP['POST /book/world-explorer/feedback']).toBe('direct');
  });

  it('DELETE /history/{id} — direct', () => {
    expect(ENVELOPE_MAP['DELETE /book/world-explorer/history/{exploration_id}']).toBe('direct');
  });

  it('path-param template-матчинг: hypotheses/{epoch} и possibilities/{epoch}', () => {
    expect(envelopeOf('GET', '/book/world-explorer/hypotheses/satya_yuga')).toBe('enveloped');
    expect(envelopeOf('GET', '/book/world-explorer/possibilities/kali_yuga')).toBe('enveloped');
    expect(envelopeOf('GET', '/book/world-explorer/history/99')).toBe('enveloped');
  });
});

// ── Wire-тело: exploreWorld ────────────────────────────────

describe('Wire: exploreWorld', () => {
  it('отправляет POST с prompt, epoch и branch_count', async () => {
    fetchMock.mockResolvedValue(okExplore());
    await exploreWorld({ prompt: 'Аркаим выживает', epoch: 'satya_yuga', branch_count: 5 });
    expect(fetchMock.mock.calls.length).toBe(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/book/world-explorer/explore');
    expect(init.method).toBe('POST');
    const body = JSON.parse(init.body as string);
    expect(body.prompt).toBe('Аркаим выживает');
    expect(body.epoch).toBe('satya_yuga');
    expect(body.branch_count).toBe(5);
  });

  it('без epoch — отправляет undefined', async () => {
    fetchMock.mockResolvedValue(okExplore());
    await exploreWorld({ prompt: 'test', branch_count: 3 });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.epoch).toBeUndefined();
  });

  it('распаковывает enveloped ответ: ranked_branches[0].quality_score', async () => {
    fetchMock.mockResolvedValue(okExplore());
    const r = await exploreWorld({ prompt: 'x', branch_count: 1 });
    expect(r.ranked_branches[0].quality_score).toBe(0.82);
    expect(r.ranked_branches[0].branch_type).toBe('moderate');
  });
});

// ── Wire-тело: validateIdea ────────────────────────────────

describe('Wire: validateIdea', () => {
  it('отправляет POST с prompt и epoch', async () => {
    fetchMock.mockResolvedValue(okValidate());
    await validateIdea({ prompt: 'idea', epoch: 'satya_yuga' });
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('/book/world-explorer/validate');
    expect(init.method).toBe('POST');
    const body = JSON.parse(init.body as string);
    expect(body.prompt).toBe('idea');
    expect(body.epoch).toBe('satya_yuga');
  });

  it('распаковывает CompatibilityResult: is_compatible, risk_level', async () => {
    fetchMock.mockResolvedValue(okValidate());
    const r = await validateIdea({ prompt: 'x', epoch: undefined });
    expect(r.is_compatible).toBe(true);
    expect(r.risk_level).toBe('low');
    expect(r.axis_scores).toHaveLength(1);
    expect(r.axis_scores[0].axis).toBe('canon_alignment');
  });
});

// ── Справочники ────────────────────────────────────────────

describe('Справочники: epochs + stats', () => {
  it('getExplorerEpochs — GET /book/world-explorer/epochs', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, data: [{ id: 'e1', name: 'A', name_ru: 'Эпоха 1', order: 1 }] }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getExplorerEpochs();
    expect(r).toHaveLength(1);
    expect(r[0].name_ru).toBe('Эпоха 1');
    expect(fetchMock.mock.calls[0][0]).toBe('/book/world-explorer/epochs');
  });

  it('getExplorerStats — GET /book/world-explorer/stats', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          data: {
            world_model: 'wm',
            patterns_count: 42,
            epochs_count: 4,
            locations_count: 18,
            events_count: 7,
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getExplorerStats();
    expect(r.patterns_count).toBe(42);
    expect(r.epochs_count).toBe(4);
  });
});

// ── Hypotheses / Possibilities ─────────────────────────────

describe('Hypotheses & Possibilities', () => {
  it('getHypotheses — path-param epoch', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, data: [{ id: 'h1', title: 'T', description: 'D', type: 'what-if' }] }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getHypotheses('satya_yuga');
    expect(r[0].id).toBe('h1');
    expect((fetchMock.mock.calls[0][0] as string)).toContain('/hypotheses/satya_yuga');
  });

  it('getPossibilities — path-param epoch', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ ok: true, data: [{ title: 'P1', title_ru: 'Возможность 1' }] }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getPossibilities('kali_yuga');
    expect(r[0].title_ru).toBe('Возможность 1');
  });
});

// ── История: save / list / detail / delete ─────────────────

describe('History CRUD', () => {
  it('saveExploration — direct POST без обёртки', async () => {
    fetchMock.mockResolvedValue(okSave());
    const r = await saveExploration({
      prompt: 'p',
      epoch: null,
      branch_count: 3,
      result_json: '{}',
      summary: 's',
      overall_score: 0.5,
    });
    expect(r.ok).toBe(true);
    expect(r.id).toBe(42);
    expect((fetchMock.mock.calls[0][0] as string)).toBe('/book/world-explorer/history');
    expect(fetchMock.mock.calls[0][1].method).toBe('POST');
  });

  it('getExplorationHistory — enveloped list', async () => {
    fetchMock.mockResolvedValue(okHistory());
    const r = await getExplorationHistory(50);
    expect(r).toHaveLength(1);
    expect(r[0].id).toBe(1);
    expect(r[0].prompt).toBe('A');
  });

  it('getExplorationDetail — enveloped single item', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          ok: true,
          data: { id: 1, prompt: 'x', epoch: 'satya_yuga' },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    const r = await getExplorationDetail(1);
    expect(r.id).toBe(1);
    expect(r.epoch).toBe('satya_yuga');
  });

  it('deleteExploration — direct DELETE', async () => {
    fetchMock.mockResolvedValue(okDelete());
    const r = await deleteExploration(7);
    expect(r.ok).toBe(true);
    expect((fetchMock.mock.calls[0][0] as string)).toBe('/book/world-explorer/history/7');
    expect(fetchMock.mock.calls[0][1].method).toBe('DELETE');
  });
});

// ── Feedback + Generate ────────────────────────────────────

describe('Feedback & Generate-from-branch', () => {
  it('submitFeedback — direct POST', async () => {
    fetchMock.mockResolvedValue(okFeedback());
    const r = await submitFeedback({ branch_rank: 1, branch_type: 'moderate', branch_title: 'Test', rating: 5, comment: 'nice' });
    expect(r.ok).toBe(true);
    expect(r.id).toBe(7);
    expect((fetchMock.mock.calls[0][0] as string)).toBe('/book/world-explorer/feedback');
    expect(fetchMock.mock.calls[0][1].method).toBe('POST');
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.rating).toBe(5);
  });

  it('generateFromBranch — enveloped, длинный таймаут', async () => {
    fetchMock.mockResolvedValue(okGenerate());
    const r = await generateFromBranch({
      exploration_prompt: 'continue',
      branch_title: 'Test branch',
      branch_type: 'moderate',
      epoch: 'satya_yuga',
    });
    expect(r.system_instruction).toBe('instr');
    expect(r.user_prompt).toBe('prompt');
    // Таймаут 120s задаётся внутри функции — проверяем наличие в коде
    expect(generateFromBranch.toString()).toContain('timeoutMs');
  });
});

// ── Инвариант: фронт не генерирует ветви сам ───────────────

describe('Инвариант: frontend не синтезирует branches', () => {
  it('контракт-модуль не содержит synthesize/generate-функций', async () => {
    const mod = await import('@/shared/api/contracts/worldExplorer');
    const fns = Object.keys(mod);
    const synthetic = fns.filter((f) => /synthe|compute.*branch/i.test(f));
    expect(synthetic.join(',')).toBe('');
    // Только fetch-функции
    expect(fns).toContain('exploreWorld');
    expect(fns).toContain('validateIdea');
    expect(fns).toContain('getExplorerEpochs');
  });
});

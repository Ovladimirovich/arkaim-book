/**
 * temporal.test.ts — F3-контракты «Время мира» + инварианты ADR_TEMPORAL §5.
 *
 * Проверяет (по live-фактам шага 0):
 *   1. ENVELOPE_MAP: все 13 temporal-записей существуют и enveloped;
 *      path-param template-матчинг работает (context/{id}, pending/{id}).
 *   2. Инвариант «фронт не синтезирует связи»: контракт-модуль не содержит
 *      генерации relations (только типы/вызовы).
 *   3. Ключевые категории provenance отображаемы (FUTURE_EXTRAPOLATION обязателен
 *      для сценариев — ADR Decision C).
 */
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ENVELOPE_MAP, envelopeOf } from '@/shared/api/envelope';
import {
  confirmFinding,
  extrapolateFuture,
  getTemporalChain,
  getTemporalNodes,
  getTemporalContext,
  getFinding,
  listPending,
  rejectFinding,
  scanBook,
  getQueueHistory,
  getQueueStats,
} from '@/shared/api/contracts/temporal';

// Использование в тестах ниже (синоним для читаемости asserts).
void getTemporalChain;

// PA-2 (post-audit): source-based инварианты — проектный паттерн login-b2.test.ts.
const CONTRACT_SRC = readFileSync('src/shared/api/contracts/temporal.ts', 'utf8');

// PA-2 (post-audit): поведенческая проверка wire-тела через fetch-mock —
// паттерн reader.test.ts (vi.stubGlobal + ok-конверт).
const fetchMock = vi.fn();
vi.stubGlobal('fetch', fetchMock);

const okFuture = () =>
  new Response(
    JSON.stringify({
      ok: true,
      data: {
        anchor_id: 'arkaim_era',
        anchor_label: 'Эпоха Аркаима',
        chain_stats: {},
        patterns_count: 0,
        scenarios: [],
        provenance: [],
        provenance_note: '',
      },
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } as Record<string, string> },
  );

afterEach(() => {
  fetchMock.mockReset();
});

describe('F3: ENVELOPE_MAP temporal-записи', () => {
  const temporalKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('/book/temporal'));

  it('9+ temporal-путей заведены (audit §2.6)', () => {
    expect(temporalKeys.length).toBeGreaterThanOrEqual(13);
  });

  it('все temporal-конверты — enveloped (live-факт: {ok, data, ...})', () => {
    for (const k of temporalKeys) {
      expect(ENVELOPE_MAP[k]).toBe('enveloped');
    }
  });

  it('path-param template-матчинг: context/{epoch_id} и pending-updates/{finding_id}', () => {
    expect(envelopeOf('GET', '/book/temporal/context/arkaim_era')).toBe('enveloped');
    expect(envelopeOf('GET', '/book/temporal/context/любая_эпоха')).toBe('enveloped');
    expect(envelopeOf('GET', '/book/temporal/pending-updates/fnd_123')).toBe('enveloped');
    expect(envelopeOf('POST', '/book/temporal/pending-updates/fnd_123/confirm')).toBe('enveloped');
    expect(envelopeOf('POST', '/book/temporal/pending-updates/fnd_123/reject')).toBe('enveloped');
  });

  it('статические пути не съедаются template-правилами (exact-приоритет)', () => {
    // /stats, /history, /scan — статические, не {finding_id}
    expect(envelopeOf('GET', '/book/temporal/pending-updates/stats')).toBe('enveloped');
    expect(envelopeOf('GET', '/book/temporal/pending-updates/history')).toBe('enveloped');
    expect(envelopeOf('POST', '/book/temporal/pending-updates/scan')).toBe('enveloped');
    expect(envelopeOf('GET', '/book/temporal/pending-updates')).toBe('enveloped');
  });

  it('нет media/backend-примесей в temporal-контрактах (Asset≠File и др.)', () => {
    // Media Plan не входит в F3: temporal-контракт — доменная temporal-модель.
    // PA-2: шим-раннер не имеет toMatch — строгий substring-фильтр по списку
    // запрещённых слов (эквивалент regex /comfyui|workflow|sdxl|steps|seed/i).
    const src = JSON.stringify(ENVELOPE_MAP) + CONTRACT_SRC;
    const banned = ['comfyui', 'workflow', 'sdxl', 'steps', 'seed'];
    const found = banned.filter((w) => src.toLowerCase().includes(w.toLowerCase()));
    expect(found.join(',')).toBe('');
  });
});

describe('F3: инвариант ADR §5 — фронт не синтезирует temporal graph', () => {
  it('контракт-модуль не генерирует relations — только читает типы', async () => {
    const mod = await import('@/shared/api/contracts/temporal');
    const fns = Object.keys(mod);
    // Никаких synthesize/generate/connect-функций.
    // PA-2: шим-раннер не имеет toMatch на массивах — filter().join() + toBe('').
    expect(fns.filter((f) => /synthe|generat|connect|link/i.test(f)).join(',')).toBe('');
    // Только fetch-функции.
    expect(fns).toContain('getTemporalChain');
    expect(fns).toContain('getTemporalNodes');
    expect(fns).toContain('extrapolateFuture');
  });

  it('«Современность» — не эпоха цепочки: контракт не создаёт today-связей', () => {
    // temporal_today приходит из /nodes (точка наблюдателя); связи — только из
    // /chain (relations). Фронт никогда не строит relation для today.
    // PA-2: toString()-подход методологически неверен (strip-types вырезает
    // типы; строка live-факта могла быть только в типе). Инвариант сильнее:
    // во всём ИСХОДНИКЕ контракта temporal_today упоминается ТОЛЬКО в
    // doc-комментарии — ни одной строки кода, оперирующей today.
    const codeLines = CONTRACT_SRC.split('\n')
      .filter((l) => !l.trim().startsWith('*') && !l.trim().startsWith('//'));
    const todayInCode = codeLines.filter((l) => l.includes('temporal_today'));
    expect(todayInCode.join('\n')).toBe('');
    // Цепочный fetch существует и берёт relations целиком из backend
    // (в коде — template-literal `/book/temporal/chain${q}` с query-параметром):
    expect(CONTRACT_SRC).toContain('`/book/temporal/chain${q}`');
    expect(CONTRACT_SRC).toContain("'/book/temporal/nodes'");
  });
});

describe('F3: M10.2-очередь — контрактные сигнатуры', () => {
  it('все 7 функций очереди существуют с корректными путями', async () => {
    expect(scanBook.toString()).toContain('/book/temporal/pending-updates/scan');
    expect(listPending.toString()).toContain('/book/temporal/pending-updates');
    expect(getQueueStats.toString()).toContain('/stats');
    expect(getQueueHistory.toString()).toContain('/history');
    expect(getFinding.toString()).toContain('/book/temporal/pending-updates/');
    expect(confirmFinding.toString()).toContain('/confirm');
    expect(rejectFinding.toString()).toContain('/reject');
    expect(rejectFinding.toString()).toContain('reason'); // ≤500 — backend RejectRequest
  });

  it('future-extrapolation — reader-гейт, wire-тело несёт max_futures', async () => {
    // PA-2: toString()-ассерт методологически неверен (strip-types вырезает
    // типы — max_futures живёт в интерфейсе FutureExtrapolationRequest).
    // Поведенческая проверка (паттерн reader.test.ts): мок сети → реальный
    // вызов контракт-функции → wire-тело запроса обязано содержать max_futures.
    fetchMock.mockResolvedValue(okFuture());
    await extrapolateFuture({ prompt: 'Что если Аркаим не пал?', max_futures: 5 });
    expect(fetchMock.mock.calls.length).toBe(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/book/temporal/future-extrapolation');
    expect(init.method).toBe('POST');
    const body = JSON.parse(init.body as string);
    expect(body.prompt).toBe('Что если Аркаим не пал?');
    expect(body.max_futures).toBe(5);
  });

  it('getTemporalContext — path-param epoch', async () => {
    expect(getTemporalContext.toString()).toContain('/book/temporal/context/');
  });

  it('getTemporalNodes — список всех узлов (включая today)', async () => {
    expect(getTemporalNodes.toString()).toContain('/book/temporal/nodes');
  });
});

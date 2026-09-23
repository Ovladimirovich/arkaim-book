/**
 * provenance-badge.test.ts — F3: ProvenanceBadge = зеркало backend-словаря.
 *
 * Инвариант (задача F3): не создавать собственную систему provenance.
 * Лейблы/цвета — SOURCE_CATEGORY_LABELS (source_levels.py:114-155).
 *
 * PA-2 (post-audit): рантайм sandbox-раннера (node strip-types) не импортирует
 * .tsx-модули — прежний value-import падал на загрузке файла целиком. Тестируем
 * по проектному паттерну source-badge.test.ts (SourceBadge.tsx, F1-набор):
 *   1) ЗЕРКАЛО: парсим backend-словарь из source_levels.py и frontend-словарь
 *      из ProvenanceBadge.tsx, сверяем 1:1 — сильнее хардкода отдельных
 *      категорий: ловит ЛЮБОЕ расхождение, включая будущие категории;
 *   2) ЛОГИКА: 1:1-копии чистых функций (categoryMeta, дедуп BadgeList) —
 *      тот же код, что в компоненте;
 *   3) ИСТОК: копии не декорация — точные строки компонента проверяются
 *      прямыми substring-ассертами.
 * (В CI настоящий vitest через vite-трансформацию исполняет файл так же.)
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

import type { ProvenanceTag } from '@/shared/api/contracts/temporal';

const FE_SRC = readFileSync('src/shared/ui/ProvenanceBadge.tsx', 'utf8');
// Backend-словарь — первоисточник маппинга (зеркалом которого обязан быть фронт).
const BE_SRC = readFileSync('../core/CORE/narrative_engine/source_levels.py', 'utf8');

// ── Парсинг словарей: FE-компонент ↔ BE-первоисточник ──

/** CATEGORY_LABELS из ProvenanceBadge.tsx (зеркало фронтенда). */
function parseFeDict(): Record<string, { label: string; color: string }> {
  const start = FE_SRC.indexOf('const CATEGORY_LABELS');
  const end = FE_SRC.indexOf('\n};', start);
  const dict = FE_SRC.slice(start, end);
  const out: Record<string, { label: string; color: string }> = {};
  const re = /([A-Z_]+):\s*\{\s*label:\s*'([^']+)',\s*color:\s*'([^']+)'/g;
  let m = re.exec(dict);
  while (m !== null) {
    out[m[1]] = { label: m[2], color: m[3] };
    m = re.exec(dict);
  }
  return out;
}

/** SOURCE_CATEGORY_LABELS из source_levels.py (первоисточник). */
function parseBeDict(): Record<string, { label: string; color: string }> {
  const start = BE_SRC.indexOf('SOURCE_CATEGORY_LABELS');
  const end = BE_SRC.indexOf('class ProvenanceTag', start);
  const dict = BE_SRC.slice(start, end);
  const out: Record<string, { label: string; color: string }> = {};
  const re = /ProvenanceCategory\.([A-Z_]+):\s*\{\s*"label":\s*"([^"]+)",\s*"color":\s*"([^"]+)"/g;
  let m = re.exec(dict);
  while (m !== null) {
    out[m[1]] = { label: m[2], color: m[3] };
    m = re.exec(dict);
  }
  return out;
}

describe('categoryMeta — зеркало SOURCE_CATEGORY_LABELS (backend)', () => {
  it('FE-словарь = BE-словарь 1:1: все категории, лейблы, цвета совпадают', () => {
    const fe = parseFeDict();
    const be = parseBeDict();
    // Ни лишних, ни недостающих категорий (в обе стороны):
    expect(Object.keys(fe).filter((k) => !(k in be)).join(',')).toBe('');
    expect(Object.keys(be).filter((k) => !(k in fe)).join(',')).toBe('');
    // Каждая запись (label+color) идентична первоисточнику:
    for (const k of Object.keys(be)) {
      expect(fe[k]).toEqual(be[k]);
    }
    // Полный набор (не выборка): все 8 категорий backend-словаря.
    expect(Object.keys(be).length).toBeGreaterThanOrEqual(8);
  });

  it('ключевые категории «Времени мира» с backend-лейблами (live-факт source_levels.py:114-155)', () => {
    const fe = parseFeDict();
    expect(fe['AUTHOR_CANON']).toEqual({ label: 'Авторский канон', color: 'green' });
    expect(fe['EXTERNAL_SOURCE']).toEqual({ label: 'Внешний источник', color: 'orange' });
    expect(fe['RECONSTRUCTION']).toEqual({ label: 'Реконструкция', color: 'purple' });
    expect(fe['HYPOTHESIS']).toEqual({ label: 'Гипотеза', color: 'gold' });
    expect(fe['FUTURE_EXTRAPOLATION']).toEqual({ label: 'Будущее extrapolation', color: 'magenta' });
    expect(fe['DERIVED']).toEqual({ label: 'Производное', color: 'blue' });
    expect(fe['ARTISTIC_MODEL']).toEqual({ label: 'Художественная модель', color: 'cyan' });
    expect(fe['UNKNOWN']).toEqual({ label: 'Неизвестно', color: 'default' });
  });

  it('неизвестная категория → UNKNOWN («Неизвестно»), не фронт-интерпретация', () => {
    // 1:1 копия чистой функции компонента (тот же код):
    const CATEGORY_LABELS = parseFeDict();
    function categoryMeta(category: string): { label: string; color: string } {
      return CATEGORY_LABELS[category] ?? CATEGORY_LABELS.UNKNOWN;
    }
    expect(categoryMeta('SOMETHING_NEW')).toEqual(categoryMeta('UNKNOWN'));
    expect(categoryMeta('UNKNOWN').label).toBe('Неизвестно');
    // Исток: fallback в компоненте реально существует (копия — не декорация):
    expect(FE_SRC).toContain('return CATEGORY_LABELS[category] ?? CATEGORY_LABELS.UNKNOWN;');
  });
});

describe('FUTURE_EXTRAPOLATION — обязательный бейдж сценариев (ADR Decision C)', () => {
  it('категория различима и уникальна (не путается с HYPOTHESIS)', () => {
    // PA-2: у шим-раннера нет .not-цепочки — эквивалент строгого not.toBe:
    // прямое сравнение + toBe(false).
    const fe = parseFeDict();
    expect(fe['FUTURE_EXTRAPOLATION'].label === fe['HYPOTHESIS'].label).toBe(false);
    expect(fe['FUTURE_EXTRAPOLATION'].color === fe['HYPOTHESIS'].color).toBe(false);
  });
});

describe('ProvenanceBadgeList — дедупликация по категории', () => {
  const tag = (category: string, confidence: number): ProvenanceTag => ({
    source_level: 'CANON',
    category,
    source_url: null,
    source_title: null,
    confidence,
    added_at: '2026-09-10T00:00:00Z',
    added_by: 'system',
    notes: '',
  });

  // 1:1 копия алгоритма дедупликации из ProvenanceBadgeList (тот же код):
  function dedupByCategory(tags: { category: string; confidence: number }[]) {
    const byCat = new Map<string, { category: string; confidence: number }>();
    for (const t of tags) {
      const cur = byCat.get(t.category);
      if (!cur || t.confidence > cur.confidence) byCat.set(t.category, t);
    }
    return [...byCat.values()];
  }

  it('пустой список → null (ранний выход компонента)', () => {
    // Компонент обязан возвращать null без рендера пустых списков:
    expect(FE_SRC).toContain('if (!tags || tags.length === 0) return null;');
  });

  it('несколько категорий → по одному бейджу на категорию (максимум confidence)', () => {
    // Рендер-смоук: якорь Аркаима — AUTHOR_CANON 1.0 + EXTERNAL_SOURCE 0.7
    // (live-факт B1/C1); дубль категории AUTHOR_CANON 0.5 поглощается 1.0.
    const tags = [
      tag('AUTHOR_CANON', 1.0),
      tag('EXTERNAL_SOURCE', 0.7),
      tag('AUTHOR_CANON', 0.5), // дубль категории — берётся максимум
    ];
    const badges = dedupByCategory(tags);
    expect(badges.length).toBe(2);
    const canon = badges.find((b) => b.category === 'AUTHOR_CANON');
    expect(canon!.confidence).toBe(1.0);
  });

  it('источник компонента: дедуп именно Map+максимум (копия — не декорация)', () => {
    expect(FE_SRC).toContain('const byCat = new Map');
    expect(FE_SRC).toContain('if (!cur || t.confidence > cur.confidence) byCat.set(t.category, t);');
  });
});

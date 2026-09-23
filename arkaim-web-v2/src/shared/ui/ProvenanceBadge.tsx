/**
 * ProvenanceBadge — бейдж provenance-категории бэкенда (F3_SPEC, ADR_TEMPORAL §5).
 *
 * Категории, лейблы и цвета — ЦЕНТРАЛИЗОВАННАЯ backend-семантика
 * (core/CORE/narrative_engine/source_levels.py: SOURCE_CATEGORY_LABELS).
 * Фронт НЕ создаёт собственную систему provenance: он отображает готовые
 * категории из ProvenanceTag и их confidence.
 *
 * Ключевые категории «Времени мира»:
 *   AUTHOR_CANON         — авторский канон (КНИГА.md)
 *   EXTERNAL_SOURCE      — внешний исторический источник
 *   RECONSTRUCTION       — реконструкция (не подтверждена каноном)
 *   HYPOTHESIS           — гипотеза/методологическая точка (temporal_today)
 *   FUTURE_EXTRAPOLATION — проекция в будущее (ОБЯЗАТЕЛЬНЫЙ бейдж сценариев,
 *                          ADR Decision C: без бейджа к показу не допускается)
 */
'use client';

import { Tag, Tooltip } from 'antd';

import type { ProvenanceTag } from '@/shared/api/contracts/temporal';

/**
 * Зеркало SOURCE_CATEGORY_LABELS (source_levels.py:114-155) — лейблы/цвета
 * backend-словаря, не фронт-интерпретация. UNKNOWN = category отсутствует
 * в словаре (показываем как «Неизвестно»).
 */
const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  AUTHOR_CANON: { label: 'Авторский канон', color: 'green' },
  DERIVED: { label: 'Производное', color: 'blue' },
  EXTERNAL_SOURCE: { label: 'Внешний источник', color: 'orange' },
  RECONSTRUCTION: { label: 'Реконструкция', color: 'purple' },
  HYPOTHESIS: { label: 'Гипотеза', color: 'gold' },
  ARTISTIC_MODEL: { label: 'Художественная модель', color: 'cyan' },
  FUTURE_EXTRAPOLATION: { label: 'Будущее extrapolation', color: 'magenta' },
  UNKNOWN: { label: 'Неизвестно', color: 'default' },
};

export function categoryMeta(category: string): { label: string; color: string } {
  return CATEGORY_LABELS[category] ?? CATEGORY_LABELS.UNKNOWN;
}

export interface ProvenanceBadgeProps {
  /** Категория из ProvenanceTag.category (backend-словарь). */
  category: string;
  /** Confidence 0..1 из тега. */
  confidence?: number;
  /** Подсказка-источник (source_title/notes) — показывается в тултипе. */
  sourceTitle?: string | null;
  notes?: string | null;
}

export function ProvenanceBadge({ category, confidence, sourceTitle, notes }: ProvenanceBadgeProps) {
  const { label, color } = categoryMeta(category);
  const conf = typeof confidence === 'number' ? ` · ${Math.round(confidence * 100)}%` : '';
  const tip = [sourceTitle, notes].filter(Boolean).join(' — ');
  return (
    <Tooltip title={tip || label}>
      <Tag color={color} style={{ marginInlineEnd: 8 }}>
        {label}
        {conf}
      </Tag>
    </Tooltip>
  );
}

/** Список provenance-тегов узла/сцены: дедупликация по категории, максимум-категорий. */
export function ProvenanceBadgeList({ tags }: { tags: ProvenanceTag[] }) {
  if (!tags || tags.length === 0) return null;
  // Один бейдж на категорию: берем тег с максимальной confidence внутри категории.
  const byCat = new Map<string, ProvenanceTag>();
  for (const t of tags) {
    const cur = byCat.get(t.category);
    if (!cur || t.confidence > cur.confidence) byCat.set(t.category, t);
  }
  return (
    <>
      {[...byCat.values()].map((t) => (
        <ProvenanceBadge
          key={t.category}
          category={t.category}
          confidence={t.confidence}
          sourceTitle={t.source_title}
          notes={t.notes}
        />
      ))}
    </>
  );
}

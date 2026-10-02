'use client';

import React from 'react';
import { LCard, LTag } from '@/shared/ui/light';
import type { WorldEntityProvenance } from '@/shared/api/contracts/world';

function present(value: string | null | undefined): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function confidencePercent(value: number | null | undefined): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1
    ? Math.round(value * 100)
    : undefined;
}

export type WorldProvenanceCardProps = {
  provenance?: WorldEntityProvenance;
};

/** Read-only provenance for a World entity. It never creates or normalizes missing data. */
export function WorldProvenanceCard({ provenance }: WorldProvenanceCardProps) {
  if (!provenance || provenance.status === 'missing') {
    return (
      <LCard title="Источник данных" bordered={false} style={{ marginTop: 16, background: 'var(--surface-bg)' }}>
        <span style={{ color: '#999' }}>Источник не указан</span>
      </LCard>
    );
  }

  const source = present(provenance.source) ? provenance.source : 'не указан';
  const sourceLevel = present(provenance.source_level) ? provenance.source_level : 'не указан';
  const percent = confidencePercent(provenance.confidence);

  return (
    <LCard title="Источник данных" bordered={false} style={{ marginTop: 16, background: 'var(--surface-bg)' }}>
      <div style={{ display: 'grid', gap: 8 }}>
        <div><strong>Источник:</strong> {source}</div>
        <div>
          <strong>Категория:</strong>{' '}
          {present(provenance.source_category)
            ? <LTag>{provenance.source_category}</LTag>
            : <span style={{ color: '#999' }}>не указан</span>}
        </div>
        <div><strong>Уровень:</strong> {sourceLevel}</div>
        {present(provenance.notes) && <div><strong>Примечания:</strong> {provenance.notes}</div>}
        {percent !== undefined && <div><strong>Уверенность:</strong> {percent}%</div>}
        {present(provenance.source_file) && <div><strong>Файл:</strong> {provenance.source_file}</div>}
      </div>
    </LCard>
  );
}
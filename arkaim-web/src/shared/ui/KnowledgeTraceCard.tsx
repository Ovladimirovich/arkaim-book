'use client';

import React, { useMemo } from 'react';
import { LCard, LTag } from '@/shared/ui/light';
import type { KnowledgeTrace, KnowledgeTraceLineageLink } from '@/shared/api/contracts/knowledge';

type RecordItem = Record<string, unknown>;

function hasEntries(value: readonly unknown[] | undefined): value is readonly RecordItem[] {
  return Array.isArray(value) && value.length > 0;
}

function arrayOf(value: unknown): readonly unknown[] {
  return Array.isArray(value) ? value : [];
}

function label(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value !== null && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    for (const key of ['claim', 'statement', 'text', 'source_ref', 'entity_id', 'label']) {
      if (typeof record[key] === 'string' && record[key]) return record[key];
    }
  }
  return 'не указано';
}

function valueAt(record: RecordItem, keys: readonly string[]): unknown {
  for (const key of keys) {
    if (record[key] !== undefined && record[key] !== null && record[key] !== '') return record[key];
  }
  return undefined;
}

function claimStatement(claim: RecordItem): string {
  return label(valueAt(claim, ['statement', 'text', 'claim']));
}

function provenanceOf(claim: RecordItem): RecordItem {
  const provenance = claim.provenance;
  return provenance !== null && typeof provenance === 'object' ? provenance as RecordItem : {};
}

function confidenceLabel(claim: RecordItem): string {
  const provenance = provenanceOf(claim);
  const value = valueAt(provenance, ['confidence']) ?? valueAt(claim, ['confidence']);
  if (typeof value === 'number') return `${Math.round(value * 100)}%`;
  if (typeof value === 'string') return value;
  return 'не указана';
}

function provenanceCategory(claim: RecordItem): string {
  const provenance = provenanceOf(claim);
  return label(valueAt(provenance, ['category', 'source_level', 'type']) ?? valueAt(claim, ['provenance_category', 'category']));
}

function sourceRef(claim: RecordItem): string {
  return label(valueAt(claim, ['source_ref', 'source']));
}

function evidenceForClaim(claim: RecordItem, evidence: readonly RecordItem[]): readonly RecordItem[] {
  const ref = sourceRef(claim);
  const chunk = label(valueAt(claim, ['chunk_id']));
  if (ref === 'не указано' && chunk === 'не указано') return evidence;
  return evidence.filter((item) => {
    const itemRef = label(valueAt(item, ['source_ref', 'source']));
    const itemChunk = label(valueAt(item, ['chunk_id']));
    return (ref !== 'не указано' && itemRef === ref) || (chunk !== 'не указано' && itemChunk === chunk);
  });
}

function temporalForClaim(claim: RecordItem, temporal: readonly RecordItem[]): readonly RecordItem[] {
  const ref = sourceRef(claim);
  if (ref === 'не указано') return temporal;
  return temporal.filter((item) => {
    const claimRef = label(valueAt(item, ['claim_ref', 'source_ref', 'claim_id']));
    return claimRef === ref;
  });
}

function temporalLabel(item: RecordItem): string {
  const claimRef = valueAt(item, ['claim_ref', 'source_ref', 'claim_id']);
  const status = valueAt(item, ['status', 'state']);
  if (claimRef !== undefined && status !== undefined) return `${label(claimRef)} · ${label(status)}`;
  return label(status ?? claimRef);
}

const TOTAL_KEYS = ['claims', 'evidence', 'conflicts', 'reasoning', 'corrections', 'lineage'] as const;

function totalsText(totals: unknown): string | null {
  if (totals === null || typeof totals !== 'object') return null;
  const record = totals as Record<string, unknown>;
  const parts: string[] = [];
  for (const key of TOTAL_KEYS) {
    if (typeof record[key] === 'number') parts.push(`${key}: ${record[key]}`);
  }
  return parts.length > 0 ? parts.join(' · ') : null;
}

function paginationText(trace: KnowledgeTrace): string {
  const offset = typeof trace.offset === 'number' ? String(trace.offset) : 'не указан';
  const limit = typeof trace.limit === 'number' ? String(trace.limit) : 'не указан';
  const next = trace.next_offset === null
    ? 'нет'
    : (typeof trace.next_offset === 'number' ? String(trace.next_offset) : 'не указано');
  return `offset ${offset}, limit ${limit}; следующая страница: ${next}`;
}

function lineageRows(link: KnowledgeTraceLineageLink): Array<{ title: string; text: string }> {
  const rows: Array<{ title: string; text: string }> = [];
  const claimLinks = arrayOf(link.claim_ids);
  if (claimLinks.length > 0) rows.push({ title: 'Claim IDs', text: claimLinks.map((v) => label(v)).join(', ') });
  const evidenceIds = arrayOf(link.evidence_ids);
  if (evidenceIds.length > 0) rows.push({ title: 'Evidence IDs', text: evidenceIds.map((v) => label(v)).join(', ') });
  const matchedClaims = arrayOf(link.claim_links);
  if (matchedClaims.length > 0) rows.push({ title: 'Claim links (matched)', text: matchedClaims.map((v) => label(v)).join(', ') });
  const evidenceLinks = arrayOf(link.evidence_links);
  if (evidenceLinks.length > 0) {
    rows.push({
      title: 'Evidence links (matched)',
      text: evidenceLinks.map((item) => {
        const record = item !== null && typeof item === 'object' ? item as RecordItem : {};
        return label(valueAt(record, ['record_id', 'source_ref']));
      }).join(', '),
    });
  }
  const reasoningIds = arrayOf(link.reasoning_ids);
  if (reasoningIds.length > 0) rows.push({ title: 'Reasoning IDs', text: reasoningIds.map((v) => label(v)).join(', ') });
  const corrections = arrayOf(link.corrections);
  if (corrections.length > 0) {
    rows.push({
      title: 'Corrections',
      text: corrections.map((item) => {
        const record = item !== null && typeof item === 'object' ? item as RecordItem : {};
        const stale = arrayOf(record.stale_reasoning_ids).map((v) => label(v)).join(', ');
        return stale ? `${label(record.correction_id)} → stale reasoning: ${stale}` : label(record.correction_id);
      }).join('; '),
    });
  }
  return rows;
}

function TraceList({ title, items }: { title: string; items: readonly unknown[] | undefined }) {
  return (
    <div>
      <p style={{ margin: '12px 0 6px' }}><strong>{title} ({hasEntries(items) ? items.length : 0})</strong></p>
      {hasEntries(items) ? (
        <ul style={{ margin: 0, paddingLeft: 20 }}>
          {items.map((item, index) => <li key={`${title}-${index}`}>{label(item)}</li>)}
        </ul>
      ) : (
        <div style={{ color: '#999' }}>Данных нет</div>
      )}
    </div>
  );
}

function DetailValue({ label: text, value }: { label: string; value: unknown }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(130px, 0.35fr) 1fr', gap: 8, marginTop: 5 }}>
      <span style={{ color: '#666' }}>{text}</span>
      <span style={{ overflowWrap: 'anywhere' }}>{label(value)}</span>
    </div>
  );
}

function ClaimDetails({ claim, index, evidence, temporal }: {
  claim: RecordItem;
  index: number;
  evidence: readonly RecordItem[];
  temporal: readonly RecordItem[];
}) {
  const claimEvidence = useMemo(() => evidenceForClaim(claim, evidence), [claim, evidence]);
  const claimTemporal = useMemo(() => temporalForClaim(claim, temporal), [claim, temporal]);
  const worldRef = valueAt(claim, ['world_ref', 'world_reference', 'world_id']);
  const claimId = valueAt(claim, ['claim_id', 'id']);

  return (
    <details style={{ marginTop: 8, borderTop: '1px solid #eee', paddingTop: 8 }}>
      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
        {index + 1}. {claimStatement(claim)}
      </summary>
      <div style={{ paddingTop: 8 }}>
        <DetailValue label="Statement" value={claimStatement(claim)} />
        <DetailValue label="Provenance category" value={provenanceCategory(claim)} />
        <DetailValue label="Confidence" value={confidenceLabel(claim)} />
        <DetailValue label="Source reference" value={sourceRef(claim)} />
        <DetailValue label="Claim ID" value={claimId} />
        <DetailValue label="World reference" value={worldRef} />
        <DetailValue label="Temporal position" value={claimTemporal.length > 0 ? temporalLabel(claimTemporal[0]) : 'не указана'} />
        <div style={{ marginTop: 8 }}>
          <strong>Evidence IDs / locators ({claimEvidence.length})</strong>
          {claimEvidence.length > 0 ? (
            <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
              {claimEvidence.map((item, evidenceIndex) => (
                <li key={`${sourceRef(claim)}-${evidenceIndex}`}>
                  <span>{label(valueAt(item, ['evidence_id', 'id', 'source_ref', 'source']))}</span>
                  <span style={{ color: '#666' }}>
                    {' · '}{label(valueAt(item, ['locator', 'chunk_id']))}
                    {typeof item.claim_id === 'string' && item.claim_id ? ` · claim: ${item.claim_id}` : ''}
                    {' · status: '}{label(valueAt(item, ['status']))}
                  </span>
                </li>
              ))}
            </ul>
          ) : <div style={{ color: '#999' }}>Данных нет</div>}
        </div>
        {claimTemporal.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <strong>Temporal references ({claimTemporal.length})</strong>
            <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
              {claimTemporal.map((item, temporalIndex) => <li key={`${sourceRef(claim)}-${temporalIndex}`}>{temporalLabel(item)}</li>)}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

export type KnowledgeTraceCardProps = {
  trace?: KnowledgeTrace;
  loading?: boolean;
  error?: string | null;
};

/**
 * Read-only projection of Knowledge Trace.
 * This component never claims, infers, normalizes or mutates knowledge.
 *
 * States: error > loading > missing trace > loaded (with/without lineage).
 */
export function KnowledgeTraceCard({ trace, loading, error }: KnowledgeTraceCardProps) {
  if (error) {
    return (
      <LCard title="Трассировка знаний" bordered={false} style={{ marginTop: 16, background: 'var(--surface-bg)' }}>
        <span style={{ color: '#c0392b' }}>{error}</span>
      </LCard>
    );
  }

  if (loading) {
    return (
      <LCard title="Трассировка знаний" bordered={false} style={{ marginTop: 16, background: 'var(--surface-bg)' }}>
        <span style={{ color: '#999' }}>Загрузка трассировки…</span>
      </LCard>
    );
  }

  if (!trace) {
    return (
      <LCard title="Трассировка знаний" bordered={false} style={{ marginTop: 16, background: 'var(--surface-bg)' }}>
        <span style={{ color: '#999' }}>Трассировка не загружена</span>
      </LCard>
    );
  }

  const claims = hasEntries(trace.claims) ? trace.claims : [];
  const evidence = hasEntries(trace.evidence) ? trace.evidence : [];
  const temporal = hasEntries(trace.temporal) ? trace.temporal : [];
  const lineage = Array.isArray(trace.lineage) ? trace.lineage : undefined;
  const totals = totalsText(trace.totals);

  return (
    <LCard title="Трассировка знаний" bordered={false} style={{ marginTop: 16, background: 'var(--surface-bg)' }}>
      <div style={{ display: 'grid', gap: 8 }}>
        <div><strong>Сущность:</strong> {trace.entity_id}</div>
        <div><strong>Полнота трассировки:</strong> <LTag color={trace.status === 'COMPLETE' ? 'green' : 'orange'}>{trace.status}</LTag></div>
        <div>
          <p style={{ margin: '12px 0 6px' }}><strong>Утверждения ({claims.length})</strong></p>
          {claims.length > 0 ? claims.map((claim, index) => (
            <ClaimDetails key={`${claimStatement(claim)}-${index}`} claim={claim} index={index} evidence={evidence} temporal={temporal} />
          )) : <div style={{ color: '#999' }}>Данных нет</div>}
        </div>
        <TraceList title="Evidence / источники" items={trace.evidence} />
        <TraceList title="Временные связи" items={trace.temporal} />
        <TraceList title="Конфликты" items={trace.conflicts} />
        <TraceList title="Рассуждения" items={trace.reasoning} />
        <TraceList title="Исправления" items={trace.corrections} />
        <div>
          <p style={{ margin: '12px 0 6px' }}><strong>Lineage ({lineage ? lineage.length : 0})</strong></p>
          {lineage === undefined ? (
            <div style={{ color: '#999' }}>Lineage отсутствует в ответе</div>
          ) : hasEntries(lineage) ? (
            lineage.map((link, index) => (
              <details key={`${label(link.conflict_id)}-${index}`} style={{ marginTop: 8, borderTop: '1px solid #eee', paddingTop: 8 }}>
                <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
                  {index + 1}. Конфликт {label(link.conflict_id)}
                </summary>
                <div style={{ paddingTop: 8 }}>
                  {lineageRows(link).map((row) => <DetailValue key={row.title} label={row.title} value={row.text} />)}
                </div>
              </details>
            ))
          ) : (
            <div style={{ color: '#999' }}>Данных нет</div>
          )}
        </div>
        <div>
          <p style={{ margin: '12px 0 6px' }}><strong>Полнота данных (totals)</strong></p>
          {totals !== null ? <div>{totals}</div> : <div style={{ color: '#999' }}>totals отсутствуют в ответе</div>}
          <div style={{ marginTop: 4, color: '#666' }}>Страница: {paginationText(trace)}</div>
        </div>
        <div>
          <p style={{ margin: '12px 0 6px' }}><strong>World reference</strong></p>
          {Object.keys(trace.world).length > 0 ? <div>{label(trace.world)}</div> : <div style={{ color: '#999' }}>World reference отсутствует</div>}
        </div>
        <div>
          <p style={{ margin: '12px 0 6px' }}><strong>Неопределённость</strong></p>
          {Object.keys(trace.uncertainty).length > 0 ? <div>{label(trace.uncertainty)}</div> : <div style={{ color: '#999' }}>Данных нет</div>}
        </div>
        <TraceList title="Ограничения" items={trace.limitations} />
      </div>
    </LCard>
  );
}
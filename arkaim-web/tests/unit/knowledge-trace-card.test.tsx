import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { KnowledgeTraceCard } from '@/shared/ui/KnowledgeTraceCard';
import type { KnowledgeTrace } from '@/shared/api/contracts/knowledge';

const trace: KnowledgeTrace = {
  entity_id: 'region_arkaim',
  status: 'PARTIAL',
  claims: [{
    claim_id: 'claim-1',
    statement: 'Аркаим — древнее городище',
    provenance: { category: 'EXTERNAL_SOURCE', confidence: 0.8 },
    source_ref: 'book:chunk:chunk-1',
    chunk_id: 'chunk-1',
    world_ref: 'world:region_arkaim',
  }],
  evidence: [{
    evidence_id: 'evidence-1',
    source_ref: 'book:chunk:chunk-1',
    chunk_id: 'chunk-1',
    source_title: 'Книга',
    status: 'RESOLVED',
    reason: 'chunk resolved',
    claim_id: 'sha256:0f2a',
  }],
  world: { entity_id: 'region_arkaim', name: 'Аркаим' },
  temporal: [{ claim_ref: 'book:chunk:chunk-1', status: 'PROJECTED_FROM_WORLD_REF' }],
  conflicts: [],
  reasoning: [{ text: 'Сопоставление источников' }],
  corrections: [],
  lineage: [{
    conflict_id: 'conflict-1',
    claim_ids: ['claim-1', 'claim-2'],
    evidence_ids: ['evidence-1'],
    claim_links: ['claim-1'],
    evidence_links: [{ record_id: 'evidence-1', source_ref: 'book:chunk:chunk-1' }],
    reasoning_ids: ['reasoning-1'],
    corrections: [{ correction_id: 'correction-1', stale_reasoning_ids: ['reasoning-2'] }],
  }],
  uncertainty: { status: 'unknown' },
  limitations: ['No resolvable evidence references in current card projection'],
  offset: 0,
  limit: 50,
  totals: { claims: 17, evidence: 25, conflicts: 4, reasoning: 2, corrections: 1, lineage: 4 },
  next_offset: null,
};

describe('KnowledgeTraceCard', () => {
  it('renders the read-only trace sections without inventing facts', () => {
    render(<KnowledgeTraceCard trace={trace} />);
    expect(screen.getByText('Трассировка знаний')).toBeTruthy();
    expect(screen.getAllByText('region_arkaim').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Аркаим — древнее городище')).toBeTruthy();
    expect(screen.getByText('Provenance category')).toBeTruthy();
    expect(screen.getByText('EXTERNAL_SOURCE')).toBeTruthy();
    expect(screen.getByText('80%')).toBeTruthy();
    expect(screen.getAllByText('book:chunk:chunk-1').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Evidence IDs / locators (1)')).toBeTruthy();
    expect(screen.getAllByText('evidence-1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/claim:\s*sha256:0f2a/)).toBeTruthy();
    expect(screen.getByText(/status:\s*RESOLVED$/)).toBeTruthy();
    expect(screen.getByText('Temporal position')).toBeTruthy();
    expect(screen.getByText('Temporal references (1)')).toBeTruthy();
    expect(screen.getByText('Сопоставление источников')).toBeTruthy();
    expect(screen.getByText('Конфликты (0)')).toBeTruthy();
    expect(screen.getAllByText('Данных нет').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Исправления (0)')).toBeTruthy();
    expect(screen.getByText('No resolvable evidence references in current card projection')).toBeTruthy();
  });

  it('renders the lineage section with cross-record links of the real projection', () => {
    render(<KnowledgeTraceCard trace={trace} />);
    expect(screen.getByText('Lineage (1)')).toBeTruthy();
    expect(screen.getByText(/Конфликт conflict-1/)).toBeTruthy();
    expect(screen.getByText('Claim IDs')).toBeTruthy();
    expect(screen.getByText('claim-1, claim-2')).toBeTruthy();
    expect(screen.getByText('Claim links (matched)')).toBeTruthy();
    expect(screen.getByText('Evidence links (matched)')).toBeTruthy();
    expect(screen.getByText('Reasoning IDs')).toBeTruthy();
    expect(screen.getByText('reasoning-1')).toBeTruthy();
    expect(screen.getByText('Corrections')).toBeTruthy();
    expect(screen.getByText(/correction-1 → stale reasoning: reasoning-2/)).toBeTruthy();
  });

  it('renders totals and pagination of the response', () => {
    render(<KnowledgeTraceCard trace={trace} />);
    expect(screen.getByText('Полнота данных (totals)')).toBeTruthy();
    expect(screen.getByText('claims: 17 · evidence: 25 · conflicts: 4 · reasoning: 2 · corrections: 1 · lineage: 4')).toBeTruthy();
    expect(screen.getByText('Страница: offset 0, limit 50; следующая страница: нет')).toBeTruthy();
  });

  it('shows the loading state while the trace is being fetched', () => {
    render(<KnowledgeTraceCard loading={true} />);
    expect(screen.getByText('Загрузка трассировки…')).toBeTruthy();
    expect(screen.queryByText('Трассировка не загружена')).toBeNull();
  });

  it('shows the API error state instead of an unloaded trace', () => {
    render(<KnowledgeTraceCard error="Не удалось загрузить трассировку" />);
    expect(screen.getByText('Не удалось загрузить трассировку')).toBeTruthy();
    expect(screen.queryByText('Трассировка не загружена')).toBeNull();
    expect(screen.queryByText('Загрузка трассировки…')).toBeNull();
  });

  it('renders an honest missing state', () => {
    render(<KnowledgeTraceCard />);
    expect(screen.getByText('Трассировка не загружена')).toBeTruthy();
  });

  it('renders empty sections and empty lineage for an entity without records', () => {
    const empty: KnowledgeTrace = {
      entity_id: 'archaeology:мехенго',
      status: 'PARTIAL',
      claims: [],
      evidence: [],
      world: {},
      temporal: [],
      conflicts: [],
      reasoning: [],
      corrections: [],
      lineage: [],
      uncertainty: {},
      limitations: ['World entity not resolved'],
      offset: 0,
      limit: 50,
      totals: { claims: 0, evidence: 0, conflicts: 0, reasoning: 0, corrections: 0, lineage: 0 },
      next_offset: null,
    };
    render(<KnowledgeTraceCard trace={empty} />);
    expect(screen.getByText('Утверждения (0)')).toBeTruthy();
    expect(screen.getByText('Lineage (0)')).toBeTruthy();
    expect(screen.getByText('World reference отсутствует')).toBeTruthy();
    expect(screen.getAllByText('Данных нет').length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText('claims: 0 · evidence: 0 · conflicts: 0 · reasoning: 0 · corrections: 0 · lineage: 0')).toBeTruthy();
  });

  it('reports a missing lineage section without inventing links', () => {
    const withoutLineage = { ...trace, entity_id: 'arkaim_settlement', lineage: undefined };
    render(<KnowledgeTraceCard trace={withoutLineage} />);
    expect(screen.getByText('Lineage (0)')).toBeTruthy();
    expect(screen.getByText('Lineage отсутствует в ответе')).toBeTruthy();
    expect(screen.queryByText(/Конфликт conflict-1/)).toBeNull();
  });

  it('shows a next page when next_offset is present', () => {
    const paginated: KnowledgeTrace = {
      ...trace,
      entity_id: 'geo_гардарика_(страна_городов)',
      offset: 50,
      limit: 10,
      next_offset: 60,
    };
    render(<KnowledgeTraceCard trace={paginated} />);
    expect(screen.getByText('Страница: offset 50, limit 10; следующая страница: 60')).toBeTruthy();
  });

  it('stays readable when the response lacks totals, next_offset and lineage', () => {
    const partial = {
      ...trace,
      entity_id: 'lang_гардарикия_(страна_городов)',
      totals: undefined,
      next_offset: undefined,
      lineage: undefined,
    } as unknown as KnowledgeTrace;
    render(<KnowledgeTraceCard trace={partial} />);
    expect(screen.getByText('totals отсутствуют в ответе')).toBeTruthy();
    expect(screen.getByText('Страница: offset 0, limit 50; следующая страница: не указано')).toBeTruthy();
    expect(screen.getByText('Lineage отсутствует в ответе')).toBeTruthy();
  });

  it('does not mutate the supplied trace object', () => {
    const snapshot = JSON.stringify(trace);
    render(<KnowledgeTraceCard trace={trace} />);
    expect(JSON.stringify(trace)).toBe(snapshot);
  });
});

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
  evidence: [{ evidence_id: 'evidence-1', source_ref: 'book:chunk:chunk-1', chunk_id: 'chunk-1', status: 'RESOLVED' }],
  world: { entity_id: 'region_arkaim', name: 'Аркаим' },
  temporal: [{ claim_ref: 'book:chunk:chunk-1', status: 'PROJECTED_FROM_WORLD_REF' }],
  conflicts: [],
  reasoning: [{ text: 'Сопоставление источников' }],
  corrections: [],
  uncertainty: { status: 'unknown' },
  limitations: ['No resolvable evidence references in current card projection'],
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
    expect(screen.getByText('evidence-1')).toBeTruthy();
    expect(screen.getByText(/status:\s*RESOLVED$/)).toBeTruthy();
    expect(screen.getByText('Temporal position')).toBeTruthy();
    expect(screen.getByText('Temporal references (1)')).toBeTruthy();
    expect(screen.getByText('Сопоставление источников')).toBeTruthy();
    expect(screen.getByText('Конфликты (0)')).toBeTruthy();
    expect(screen.getAllByText('Данных нет').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Исправления (0)')).toBeTruthy();
    expect(screen.getByText('No resolvable evidence references in current card projection')).toBeTruthy();
  });

  it('renders an honest missing state', () => {
    render(<KnowledgeTraceCard />);
    expect(screen.getByText('Трассировка не загружена')).toBeTruthy();
  });

  it('does not mutate the supplied trace object', () => {
    const snapshot = JSON.stringify(trace);
    render(<KnowledgeTraceCard trace={trace} />);
    expect(JSON.stringify(trace)).toBe(snapshot);
  });
});
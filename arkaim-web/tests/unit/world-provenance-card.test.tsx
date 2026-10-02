import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorldProvenanceCard } from '@/shared/ui/WorldProvenanceCard';
import type { WorldEntityProvenance } from '@/shared/api/contracts/world';

describe('WorldProvenanceCard', () => {
  it('renders available provenance without inventing missing values', () => {
    const provenance: WorldEntityProvenance = {
      status: 'available',
      source: 'MAP_DATA.json',
      source_category: 'EXTERNAL_SOURCE',
      source_level: 'HISTORICAL',
      notes: 'Картографические данные',
      confidence: 0.8,
      source_file: null,
    };
    render(<WorldProvenanceCard provenance={provenance} />);
    expect(screen.getByText('Источник данных')).toBeTruthy();
    expect(screen.getByText('MAP_DATA.json')).toBeTruthy();
    expect(screen.getByText('EXTERNAL_SOURCE')).toBeTruthy();
    expect(screen.getByText('HISTORICAL')).toBeTruthy();
    expect(screen.getByText('Картографические данные')).toBeTruthy();
    expect(screen.getByText('80%')).toBeTruthy();
    expect(screen.queryByText('Файл:')).toBeNull();
  });

  it('renders an honest missing state and does not render a fake percentage', () => {
    render(<WorldProvenanceCard provenance={{ status: 'missing' }} />);
    expect(screen.getByText('Источник не указан')).toBeTruthy();
    expect(screen.queryByText('0%')).toBeNull();
    expect(screen.queryByText('NaN%')).toBeNull();
  });

  it('does not mutate the supplied provenance object', () => {
    const provenance: WorldEntityProvenance = { status: 'available', source: 'source.json', confidence: 0.4 };
    const snapshot = JSON.stringify(provenance);
    render(<WorldProvenanceCard provenance={provenance} />);
    expect(JSON.stringify(provenance)).toBe(snapshot);
  });
});
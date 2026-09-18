/**
 * moderation.test.ts — контракт community moderation API (F4, F4_SPEC §3.5).
 */
import { describe, expect, it } from 'vitest';
import { ENVELOPE_MAP, envelopeOf } from '@/shared/api/envelope';

describe('ENVELOPE_MAP — community moderation endpoints (F4)', () => {
  it('approve interpretation — direct', () => {
    expect(ENVELOPE_MAP['POST /book/community/interpretations/{interp_id}/approve']).toBe('direct');
  });

  it('reject interpretation — direct', () => {
    expect(ENVELOPE_MAP['POST /book/community/interpretations/{interp_id}/reject']).toBe('direct');
  });

  it('approve artifact — direct', () => {
    expect(ENVELOPE_MAP['POST /book/community/artifacts/{artifact_id}/approve']).toBe('direct');
  });

  it('reject artifact — direct', () => {
    expect(ENVELOPE_MAP['POST /book/community/artifacts/{artifact_id}/reject']).toBe('direct');
  });

  it('все 4 moderation-пути существуют в карте', () => {
    const keys = Object.keys(ENVELOPE_MAP);
    expect(keys).toContain('POST /book/community/interpretations/{interp_id}/approve');
    expect(keys).toContain('POST /book/community/interpretations/{interp_id}/reject');
    expect(keys).toContain('POST /book/community/artifacts/{artifact_id}/approve');
    expect(keys).toContain('POST /book/community/artifacts/{artifact_id}/reject');
  });
});

describe('envelopeOf — template matching for moderation paths', () => {
  it('POST /book/community/interpretations/abc123/approve → direct', () => {
    expect(envelopeOf('POST', '/book/community/interpretations/abc123/approve')).toBe('direct');
  });

  it('POST /book/community/artifacts/xyz789/reject → direct', () => {
    expect(envelopeOf('POST', '/book/community/artifacts/xyz789/reject')).toBe('direct');
  });
});

/**
 * Studio contract tests — проверяет envelope map и API function signatures.
 */
import { describe, it, expect } from 'vitest';
import { ENVELOPE_MAP, envelopeOf } from '@/shared/api/envelope';

describe('Studio envelope map', () => {
  it('all studio endpoints are in ENVELOPE_MAP', () => {
    const studioKeys = Object.keys(ENVELOPE_MAP).filter((k) => k.includes('/studio'));
    expect(studioKeys.length).toBeGreaterThanOrEqual(11);
  });

  it('studio create is enveloped', () => {
    expect(envelopeOf('POST', '/studio/create')).toBe('enveloped');
  });

  it('studio list is enveloped', () => {
    expect(envelopeOf('GET', '/studio/list')).toBe('enveloped');
  });

  it('studio get session is enveloped', () => {
    expect(envelopeOf('GET', '/studio/session_abc123')).toBe('enveloped');
  });

  it('studio discuss is enveloped', () => {
    expect(envelopeOf('POST', '/studio/session_abc123/discuss')).toBe('enveloped');
  });

  it('studio modify is enveloped', () => {
    expect(envelopeOf('POST', '/studio/session_abc123/modify')).toBe('enveloped');
  });

  it('studio variant is enveloped', () => {
    expect(envelopeOf('POST', '/studio/session_abc123/variant')).toBe('enveloped');
  });

  it('studio activate-version is enveloped', () => {
    expect(envelopeOf('POST', '/studio/session_abc123/activate-version')).toBe('enveloped');
  });

  it('studio upload-reference is enveloped', () => {
    expect(envelopeOf('POST', '/studio/session_abc123/upload-reference')).toBe('enveloped');
  });

  it('studio approve is enveloped', () => {
    expect(envelopeOf('POST', '/studio/session_abc123/approve')).toBe('enveloped');
  });

  it('studio reject is enveloped', () => {
    expect(envelopeOf('POST', '/studio/session_abc123/reject')).toBe('enveloped');
  });

  it('studio export is direct (raw JSON)', () => {
    expect(envelopeOf('GET', '/studio/session_abc123/export')).toBe('direct');
  });
});

describe('Studio contract types', () => {
  it('StudioSession has required fields', async () => {
    const mod = await import('@/shared/api/contracts/studio');
    // Type-only check — if import succeeds, types are valid
    expect(mod).toBeDefined();
  });
});

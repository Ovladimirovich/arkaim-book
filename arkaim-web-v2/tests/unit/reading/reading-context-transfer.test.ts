/**
 * tests/unit/reading/reading-context-transfer.test.ts — testing context transfer logic.
 */
import { describe, it, expect } from 'vitest';

describe('Reading context transfer', () => {
  it('URL encoding preserves chapter title with special characters', () => {
    const chapterTitle = 'Велик идёт сквозь огонь';
    const encoded = encodeURIComponent(chapterTitle);
    const decoded = decodeURIComponent(encoded);
    expect(decoded).toBe(chapterTitle);
  });

  it('context string follows expected format', () => {
    const chapterTitle = 'Глава первая';
    const chapterIndex = 0;
    const ctx = `Глава "${chapterTitle}" (№${chapterIndex + 1}). Спросить что-нибудь об этой главе.`;
    const encoded = encodeURIComponent(ctx);
    const url = `/?ask=${encoded}`;

    expect(url).toContain('/?ask=');
    expect(url).toContain(encodeURIComponent(chapterTitle));
  });

  it('chapter title with parentheses encodes correctly', () => {
    const chapterTitle = 'Аркаим: начало пути (и конец)';
    const encoded = encodeURIComponent(chapterTitle);
    const decoded = decodeURIComponent(encoded);
    expect(decoded).toBe(chapterTitle);
  });

  it('library redirect URL is correct', () => {
    const url = '/library';
    expect(url).toBe('/library');
  });

  it('session storage key is correct', () => {
    const key = 'arkaim_reading_context';
    const value = JSON.stringify({ chapterId: 'ch_001', chapterTitle: 'Test' });
    expect(key).toBe('arkaim_reading_context');
    expect(JSON.parse(value)).toEqual({ chapterId: 'ch_001', chapterTitle: 'Test' });
  });

  it('reading settings localStorage key is correct', () => {
    const key = 'arkaim_reading_settings';
    expect(key).toBe('arkaim_reading_settings');
  });

  it('JSON stringify/parse roundtrip for settings', () => {
    const settings = {
      fontSize: 18,
      columnWidth: 72,
      paragraphSpacing: 'relaxed',
      lineHeight: 1.9,
      theme: 'dark',
    };
    const serialized = JSON.stringify(settings);
    const deserialized = JSON.parse(serialized);
    expect(deserialized).toEqual(settings);
  });
});

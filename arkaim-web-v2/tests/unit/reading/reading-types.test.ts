/**
 * tests/unit/reading/reading-types.test.ts — testing Reading types and helpers.
 */
import { describe, it, expect } from 'vitest';
import {
  DEFAULT_READING_SETTINGS,
  columnWidthPx,
  paragraphSpacingPx,
  type ReadingSettings,
  type FontSize,
  type ParagraphSpacing,
} from '@/entities/reader/types';

describe('Reading types and helpers', () => {
  describe('DEFAULT_READING_SETTINGS', () => {
    it('has correct defaults', () => {
      expect(DEFAULT_READING_SETTINGS.fontSize).toBe(17);
      expect(DEFAULT_READING_SETTINGS.lineHeight).toBe(1.8);
      expect(DEFAULT_READING_SETTINGS.paragraphSpacing).toBe('normal');
      expect(DEFAULT_READING_SETTINGS.theme).toBe('auto');
      expect(DEFAULT_READING_SETTINGS.columnWidth).toBe(68);
    });
  });

  describe('columnWidthPx', () => {
    it('maps fontSize 15 to 540px', () => {
      expect(columnWidthPx(15)).toBe(540);
    });
    it('maps fontSize 17 to 612px', () => {
      expect(columnWidthPx(17)).toBe(612);
    });
    it('maps fontSize 20 to 720px', () => {
      expect(columnWidthPx(20)).toBe(720);
    });
    it('all sizes map to positive numbers', () => {
      const sizes: FontSize[] = [15, 16, 17, 18, 19, 20];
      for (const size of sizes) {
        const px = columnWidthPx(size);
        expect(typeof px).toBe('number');
        expect(px > 0).toBe(true);
      }
    });
    it('returns same value for same input (pure function)', () => {
      expect(columnWidthPx(18)).toBe(columnWidthPx(18));
    });
  });

  describe('paragraphSpacingPx', () => {
    it('maps compact to 0.8em', () => {
      expect(paragraphSpacingPx('compact')).toBe(0.8);
    });
    it('maps normal to 1.2em', () => {
      expect(paragraphSpacingPx('normal')).toBe(1.2);
    });
    it('maps relaxed to 1.6em', () => {
      expect(paragraphSpacingPx('relaxed')).toBe(1.6);
    });
  });

  describe('ReadingSettings type', () => {
    it('accepts valid settings object', () => {
      const valid: ReadingSettings = {
        fontSize: 18,
        columnWidth: 72,
        paragraphSpacing: 'relaxed',
        lineHeight: 1.9,
        theme: 'dark',
      };
      expect(valid.fontSize).toBe(18);
      expect(valid.theme).toBe('dark');
    });

    it('accepts light theme', () => {
      const settings: ReadingSettings = {
        fontSize: 17,
        columnWidth: 68,
        paragraphSpacing: 'normal',
        lineHeight: 1.8,
        theme: 'light',
      };
      expect(settings.theme).toBe('light');
    });

    it('accepts auto theme', () => {
      const settings: ReadingSettings = {
        fontSize: 17,
        columnWidth: 68,
        paragraphSpacing: 'normal',
        lineHeight: 1.8,
        theme: 'auto',
      };
      expect(settings.theme).toBe('auto');
    });
  });
});

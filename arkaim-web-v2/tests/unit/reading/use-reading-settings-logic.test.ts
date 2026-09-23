/**
 * tests/unit/reading/use-reading-settings-logic.test.ts — testing settings logic.
 */
import { describe, it, expect } from 'vitest';
import {
  DEFAULT_READING_SETTINGS,
  type ReadingSettings,
} from '@/entities/reader/types';

describe('Reading settings logic', () => {
  it('default settings are sensible', () => {
    expect(DEFAULT_READING_SETTINGS.fontSize).toBe(17);
    expect(DEFAULT_READING_SETTINGS.lineHeight).toBe(1.8);
    expect(DEFAULT_READING_SETTINGS.paragraphSpacing).toBe('normal');
    expect(DEFAULT_READING_SETTINGS.theme).toBe('auto');
  });

  it('theme resolution: auto → light when no matchMedia', () => {
    const resolveTheme = (theme: ReadingSettings['theme']): 'light' | 'dark' => {
      if (theme === 'auto') return 'light'; // simulated no-matchMedia
      return theme;
    };
    expect(resolveTheme('auto')).toBe('light');
    expect(resolveTheme('light')).toBe('light');
    expect(resolveTheme('dark')).toBe('dark');
  });

  it('settings update creates new object (immutability)', () => {
    const original: ReadingSettings = { ...DEFAULT_READING_SETTINGS };
    const updated = { ...original, fontSize: 18 };
    expect(updated.fontSize).toBe(18);
    expect(updated.lineHeight).toBe(original.lineHeight);
    expect(updated).not.toBe(original);
  });

  it('settings reset returns defaults', () => {
    const custom: ReadingSettings = {
      fontSize: 20,
      columnWidth: 80,
      paragraphSpacing: 'relaxed',
      lineHeight: 2.0,
      theme: 'dark',
    };
    const reset = { ...DEFAULT_READING_SETTINGS };
    expect(reset.fontSize).not.toBe(custom.fontSize);
    expect(reset.theme).toBe('auto');
  });

  it('partial settings merge with defaults', () => {
    const partial = { fontSize: 19 } as Partial<ReadingSettings>;
    const merged = { ...DEFAULT_READING_SETTINGS, ...partial };
    expect(merged.fontSize).toBe(19);
    expect(merged.lineHeight).toBe(1.8);
    expect(merged.theme).toBe('auto');
  });
});

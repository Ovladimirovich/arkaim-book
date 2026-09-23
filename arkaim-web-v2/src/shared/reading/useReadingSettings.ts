/**
 * shared/reading/useReadingSettings.ts — perzistentnye nastavleniya chteniya.
 */
'use client';

import { useState, useCallback } from 'react';
import {
  DEFAULT_READING_SETTINGS,
  type ReadingSettings,
} from '@/entities/reader/types';

const STORAGE_KEY = 'arkaim_reading_settings';

function loadFromStorage(): ReadingSettings | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ReadingSettings>;
    if (
      typeof parsed.fontSize !== 'number' ||
      typeof parsed.lineHeight !== 'number' ||
      !parsed.paragraphSpacing ||
      !parsed.theme
    ) {
      return null;
    }
    return { ...DEFAULT_READING_SETTINGS, ...parsed };
  } catch {
    return null;
  }
}

function saveToStorage(s: ReadingSettings): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    // ignore
  }
}

function resolveTheme(theme: ReadingSettings['theme']): 'light' | 'dark' {
  if (theme === 'auto') {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return theme;
}

export function useReadingSettings() {
  const [settings, setSettings] = useState<ReadingSettings>(() =>
    loadFromStorage() ?? DEFAULT_READING_SETTINGS,
  );

  // Compute effective theme synchronously from settings (no effect needed)
  const effectiveTheme = resolveTheme(settings.theme);

  const update = useCallback(<K extends keyof ReadingSettings>(key: K, value: ReadingSettings[K]) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      saveToStorage(next);
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    const def = DEFAULT_READING_SETTINGS;
    setSettings(def);
    saveToStorage(def);
  }, []);

  return { settings, effectiveTheme, update, reset };
}

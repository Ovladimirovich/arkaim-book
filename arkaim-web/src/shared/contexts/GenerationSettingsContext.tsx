'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

export type Provider = 'auto' | 'comfyui' | 'mock';
export type Quality = 'draft' | 'standard' | 'high' | 'ultra';

export interface GenerationSettings {
  provider: Provider;
  style: string;
  mood: string;
  size: string;
  negativePrompt: string;
  quality: Quality;
  updateSettings: (updates: Partial<GenerationSettings>) => void;
  resetSettings: () => void;
}

const STORAGE_KEY = 'generation_settings';

const DEFAULT_SETTINGS: Omit<GenerationSettings, 'updateSettings' | 'resetSettings'> = {
  provider: 'auto',
  style: 'cinematic_fantasy',
  mood: 'neutral',
  size: '1024x1024',
  negativePrompt: '',
  quality: 'standard',
};

function loadSettings(): typeof DEFAULT_SETTINGS {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return { ...DEFAULT_SETTINGS, ...parsed };
    }
  } catch {}
  return DEFAULT_SETTINGS;
}

function saveSettings(settings: typeof DEFAULT_SETTINGS) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {}
}

const GenerationSettingsContext = createContext<GenerationSettings | null>(null);

export function GenerationSettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState(loadSettings);

  const updateSettings = useCallback((updates: Partial<typeof DEFAULT_SETTINGS>) => {
    setSettings(prev => {
      const next = { ...prev, ...updates };
      saveSettings(next);
      return next;
    });
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
    saveSettings(DEFAULT_SETTINGS);
  }, []);

  return (
    <GenerationSettingsContext.Provider value={{ ...settings, updateSettings, resetSettings }}>
      {children}
    </GenerationSettingsContext.Provider>
  );
}

export function useGenerationSettings(): GenerationSettings {
  const ctx = useContext(GenerationSettingsContext);
  if (!ctx) {
    throw new Error('useGenerationSettings must be used within a GenerationSettingsProvider');
  }
  return ctx;
}

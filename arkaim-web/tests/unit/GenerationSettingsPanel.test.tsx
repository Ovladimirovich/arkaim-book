import React from 'react';
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useGenerationSettings, GenerationSettingsProvider } from '@/shared/contexts/GenerationSettingsContext';

function Wrapper({ children }: { children: React.ReactNode }) {
  return <GenerationSettingsProvider>{children}</GenerationSettingsProvider>;
}

function renderSettingsHook() {
  return renderHook(() => useGenerationSettings(), { wrapper: Wrapper });
}

describe('GenerationSettings Context', () => {
  it('should have default settings', () => {
    const { result } = renderSettingsHook();

    expect(result.current.provider).toBe('auto');
    expect(result.current.style).toBe('cinematic_fantasy');
    expect(result.current.mood).toBe('neutral');
    expect(result.current.size).toBe('1024x1024');
    expect(result.current.negativePrompt).toBe('');
    expect(result.current.quality).toBe('standard');
  });

  it('should update quality', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({ quality: 'high' });
    });

    expect(result.current.quality).toBe('high');
  });

  it('should update provider', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({ provider: 'comfyui' });
    });

    expect(result.current.provider).toBe('comfyui');
  });

  it('should update style', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({ style: 'realistic' });
    });

    expect(result.current.style).toBe('realistic');
  });

  it('should update mood', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({ mood: 'joy' });
    });

    expect(result.current.mood).toBe('joy');
  });

  it('should update size', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({ size: '512x512' });
    });

    expect(result.current.size).toBe('512x512');
  });

  it('should update negative prompt', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({ negativePrompt: 'blurry, cartoon' });
    });

    expect(result.current.negativePrompt).toBe('blurry, cartoon');
  });

  it('should update multiple settings at once', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({
        provider: 'comfyui',
        style: 'watercolor',
        mood: 'sadness',
        size: '768x768',
      });
    });

    expect(result.current.provider).toBe('comfyui');
    expect(result.current.style).toBe('watercolor');
    expect(result.current.mood).toBe('sadness');
    expect(result.current.size).toBe('768x768');
  });

  it('should reset to default settings', () => {
    const { result } = renderSettingsHook();

    act(() => {
      result.current.updateSettings({
        provider: 'comfyui',
        style: 'dark_gothic',
        mood: 'anger',
        size: '512x512',
        negativePrompt: 'test',
      });
    });

    expect(result.current.provider).toBe('comfyui');
    expect(result.current.style).toBe('dark_gothic');

    act(() => {
      result.current.resetSettings();
    });

    expect(result.current.provider).toBe('auto');
    expect(result.current.style).toBe('cinematic_fantasy');
    expect(result.current.mood).toBe('neutral');
    expect(result.current.size).toBe('1024x1024');
    expect(result.current.negativePrompt).toBe('');
    expect(result.current.quality).toBe('standard');
  });
});

'use client';

import { useMutation } from '@tanstack/react-query';
import { useGenerationSettings } from '../contexts/GenerationSettingsContext';

type GenerateImageParams = {
  chapter: number;
  scene_id: string;
  style?: string;
  mood?: string;
  quality?: string;
  provider?: string;
  size?: string;
  negative_prompt?: string;
};

type GenerateImageResult = {
  data?: {
    id?: string;
    file_path?: string;
    prompt?: string;
    provider?: string;
  };
};

export function useGenerateImage() {
  const globalSettings = useGenerationSettings();

  return useMutation<GenerateImageResult, Error, GenerateImageParams>({
    mutationFn: async (params) => {
      const query = new URLSearchParams({
        chapter: String(params.chapter),
        scene_id: params.scene_id,
        style: params.style || globalSettings.style,
        mood: params.mood || globalSettings.mood,
        quality: params.quality || globalSettings.quality,
        provider: params.provider || globalSettings.provider,
        size: params.size || globalSettings.size,
        negative_prompt: params.negative_prompt || globalSettings.negativePrompt,
      });
      const res = await fetch(`/book/assets/generate?${query}`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Generation failed');
      }
      return res.json();
    },
  });
}

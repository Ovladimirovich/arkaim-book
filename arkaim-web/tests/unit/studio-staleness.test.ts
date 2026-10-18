import { describe, it, expect } from 'vitest';
import {
  imageMatchesPrompt,
  isImageOutdated,
  isMockGeneration,
  videoKindLabel,
  videoOutdatedReasons,
} from '@/app/studio/staleness';
import type { JobAsset } from '@/app/studio/types';

function videoAsset(over: Partial<JobAsset> = {}): JobAsset {
  return {
    asset_id: 'vid_1',
    asset_type: 'video',
    chapter: 1,
    scene_id: 'scene_1',
    title: 'клип',
    status: 'completed',
    file_path: 'videos/vid_1.mp4',
    error: null,
    ...over,
  };
}

function imageAsset(over: Partial<JobAsset> = {}): JobAsset {
  return {
    asset_id: 'img_1',
    asset_type: 'image',
    chapter: 1,
    scene_id: 'scene_1',
    title: 'кадр',
    status: 'completed',
    file_path: 'images/img_1.png',
    error: null,
    ...over,
  };
}

describe('staleness — изображения', () => {
  it('совпадение промпта: trim + схлопывание пробелов', () => {
    expect(imageMatchesPrompt(imageAsset({ prompt_used: '  кадр   аркаима ' }), 'кадр аркаима')).toBe(true);
    expect(imageMatchesPrompt(imageAsset({ prompt_used: 'кадр аркаима' }), 'кадр иной')).toBe(false);
  });

  it('без данных о промпте — не объявляем устаревшим', () => {
    expect(isImageOutdated(imageAsset({ prompt_used: '' }), 'текущий промпт')).toBe(false);
    expect(isImageOutdated(imageAsset({ prompt_used: 'создан по старому' }), '')).toBe(false);
  });

  it('готовый кадр по прежнему промпту — требует обновления', () => {
    expect(isImageOutdated(imageAsset({ prompt_used: 'прежний' }), 'текущий')).toBe(true);
    expect(isImageOutdated(imageAsset({ prompt_used: 'текущий' }), 'текущий')).toBe(false);
  });

  it('неготовый кадр — не оцениваем', () => {
    expect(isImageOutdated(imageAsset({ status: 'generating', prompt_used: 'прежний' }), 'текущий')).toBe(false);
    expect(isImageOutdated(imageAsset({ status: 'failed', prompt_used: 'прежний' }), 'текущий')).toBe(false);
  });
});

describe('staleness — видео', () => {
  it('исходный кадр не совпадает с утверждённым — причина', () => {
    const asset = videoAsset({
      prompt_used: 'движение',
      generation: { reference_image_id: 'img_old' },
    });
    const reasons = videoOutdatedReasons(asset, {
      approvedImageAssetId: 'img_new',
      currentFullPrompt: 'движение',
    });
    expect(reasons).toHaveLength(1);
    expect(reasons[0]).toContain('не совпадает с утверждённым');
  });

  it('видео без кадра при наличии утверждённого — причина', () => {
    const asset = videoAsset({ prompt_used: 'движение', generation: {} });
    const reasons = videoOutdatedReasons(asset, {
      approvedImageAssetId: 'img_new',
      currentFullPrompt: 'движение',
    });
    expect(reasons.some((r) => r.includes('без утверждённого кадра'))).toBe(true);
  });

  it('промпт движения изменился — причина', () => {
    const asset = videoAsset({
      prompt_used: 'старое движение',
      generation: { reference_image_id: 'img_1' },
    });
    const reasons = videoOutdatedReasons(asset, {
      approvedImageAssetId: 'img_1',
      currentFullPrompt: 'новое движение',
    });
    expect(reasons.some((r) => r.includes('промпт движения изменился'))).toBe(true);
  });

  it('кадр и промпт совпадают — не устарело', () => {
    const asset = videoAsset({
      prompt_used: 'движение',
      generation: { reference_image_id: 'img_1' },
    });
    expect(
      videoOutdatedReasons(asset, {
        approvedImageAssetId: 'img_1',
        currentFullPrompt: 'движение',
      }),
    ).toEqual([]);
  });

  it('утверждённого кадра нет — про кадр причин не выводим (только промпт)', () => {
    const asset = videoAsset({ prompt_used: 'движение', generation: {} });
    expect(
      videoOutdatedReasons(asset, {
        approvedImageAssetId: null,
        currentFullPrompt: 'движение',
      }),
    ).toEqual([]);
  });

  it('неготовое видео не оцениваем', () => {
    const asset = videoAsset({ status: 'generating', prompt_used: 'старое' });
    expect(
      videoOutdatedReasons(asset, { approvedImageAssetId: 'img_1', currentFullPrompt: 'новое' }),
    ).toEqual([]);
  });
});

describe('staleness — mock vs реальный клип', () => {
  it('mock по provider или backend', () => {
    expect(isMockGeneration({ generation: { provider: 'mock' } })).toBe(true);
    expect(isMockGeneration({ generation: { provider: 'comfyicu', backend: 'mock' } })).toBe(true);
    expect(isMockGeneration({ generation: { provider: 'comfyicu', backend: 'comfyicu' } })).toBe(false);
    expect(isMockGeneration(undefined)).toBe(false);
  });

  it('подписи бейджа', () => {
    expect(videoKindLabel(videoAsset({ generation: { provider: 'mock' } }))).toContain('mock-запись');
    expect(videoKindLabel(videoAsset({ generation: { provider: 'comfyicu' } }))).toBe('реальный клип');
    expect(videoKindLabel(videoAsset({ status: 'generating' }))).toBe('');
  });
});

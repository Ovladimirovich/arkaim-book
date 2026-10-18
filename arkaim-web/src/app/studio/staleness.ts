/**
 * Зависимости артефактов Studio (staleness — вычисление сравнением, без хранения).
 *
 * Правила (OWNER-GO, приняты):
 *  - изображение «требует обновления», если его prompt_used != текущий
 *    image_description.prompt;
 *  - видео «потенциально устарело», если reference_image_id !=
 *    session.approved_image_asset_id (при наличии утверждённого кадра)
 *    ИЛИ prompt_used != собранный текущий fullPrompt;
 *  - правка содержания сцены (video_scenario) НЕ помечает кадры/видео:
 *    нет влияния → не объявлять устаревшим;
 *  - ничего не удаляется и не снимается с утверждения автоматически;
 *  - без данных (пустой prompt_used) — не объявляем устаревшим.
 *
 * Чистые функции: используются в панелях и покрыты unit-тестами.
 */
import type { GenerationInfo, JobAsset } from './types';

type Norm = (s: string | null | undefined) => string;

const norm: Norm = (s) => (s || '').replace(/\s+/g, ' ').trim();

/** Изображение сделано по текущему промпту? */
export function imageMatchesPrompt(
  asset: Pick<JobAsset, 'prompt_used'>,
  currentPrompt: string,
): boolean {
  const used = norm(asset.prompt_used);
  const current = norm(currentPrompt);
  if (!used || !current) return false;
  return used === current;
}

/**
 * Кадр «требует обновления»: готов, промпт генерации известен и отличается
 * от текущего image_description.prompt.
 */
export function isImageOutdated(
  asset: Pick<JobAsset, 'status' | 'prompt_used'>,
  currentPrompt: string,
): boolean {
  if (asset.status !== 'completed') return false;
  const used = norm(asset.prompt_used);
  const current = norm(currentPrompt);
  if (!used || !current) return false;
  return used !== current;
}

export type VideoOutdatedContext = {
  /** session.approved_image_asset_id (null — кадр не утверждён). */
  approvedImageAssetId?: string | null;
  /** Текущий собранный fullPrompt (video_description.prompt + движение). */
  currentFullPrompt: string;
};

/**
 * Причины, по которым видео «потенциально устарело».
 * Пустой список — видео соответствует текущим промпту и утверждённому кадру.
 */
export function videoOutdatedReasons(asset: JobAsset, ctx: VideoOutdatedContext): string[] {
  if (asset.status !== 'completed') return [];
  const reasons: string[] = [];

  const approved = ctx.approvedImageAssetId || null;
  if (approved) {
    const ref = asset.generation?.reference_image_id || null;
    if (ref !== approved) {
      reasons.push(
        ref
          ? `исходный кадр (${ref}) не совпадает с утверждённым (${approved})`
          : 'создано без утверждённого кадра-основы',
      );
    }
  }

  const used = norm(asset.prompt_used);
  const current = norm(ctx.currentFullPrompt);
  if (used && current && used !== current) {
    reasons.push('промпт движения изменился после генерации');
  }

  return reasons;
}

/** mock-запись (без реального видео) vs реальный клип. */
export function isMockGeneration(
  assetOrGen: JobAsset | { generation?: GenerationInfo } | GenerationInfo | undefined,
): boolean {
  if (!assetOrGen) return false;
  const gen: GenerationInfo | undefined =
    'generation' in assetOrGen ? assetOrGen.generation : (assetOrGen as GenerationInfo);
  if (!gen) return false;
  return gen.provider === 'mock' || gen.backend === 'mock';
}

/** Подпись для бейджа: mock-запись или реальный клип. */
export function videoKindLabel(asset: JobAsset): string {
  if (asset.status !== 'completed') return '';
  return isMockGeneration(asset) ? 'mock-запись (без реального видео)' : 'реальный клип';
}

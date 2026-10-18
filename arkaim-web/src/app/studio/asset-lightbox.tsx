'use client';

import { LAlert, LModal, LSpace, LTag } from '@/shared/ui/light';
import { assetFileUrl } from './types';
import type { JobAsset } from './types';

type Props = {
  asset: JobAsset | null;
  open: boolean;
  onClose: () => void;
  approved?: boolean;
  /** Текущий image_description.prompt — для пометки «промпт изменился». */
  currentPrompt?: string;
  outdated?: boolean;
};

/** Просмотр ассета в полном размере с происхождением (промпт, провенанс). */
export function AssetLightbox({ asset, open, onClose, approved, currentPrompt, outdated }: Props) {
  if (!asset) return null;
  const gen = asset.generation || {};

  return (
    <LModal
      open={open}
      title={asset.title || asset.asset_id}
      onCancel={onClose}
      width={880}
      footer={null}
    >
      <div>
        {asset.status === 'completed' && asset.file_path ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={assetFileUrl(asset.asset_id)}
            alt={asset.title || asset.asset_id}
            data-testid="lightbox-image"
            style={{
              width: '100%',
              maxHeight: '60vh',
              objectFit: 'contain',
              display: 'block',
              borderRadius: 8,
              background: '#111',
            }}
          />
        ) : (
          <LAlert type="info" showIcon message="Изображение ещё не готово или недоступно" />
        )}

        <LSpace wrap style={{ marginTop: 12 }}>
          <LTag>{asset.asset_id}</LTag>
          {approved && <LTag color="success">утверждённый кадр</LTag>}
          {outdated && <LTag color="orange">создан по прежнему промпту</LTag>}
          {gen.provider && <LTag>исполнитель: {gen.provider}</LTag>}
          {gen.backend && gen.backend !== gen.provider && <LTag>бэкенд: {gen.backend}</LTag>}
          {gen.workflow_used && <LTag color="purple">workflow: {gen.workflow_used}</LTag>}
          {gen.plan_id && <LTag color="blue">план: {gen.plan_id}</LTag>}
          {gen.media_id && <LTag>media: {gen.media_id}</LTag>}
          {gen.input_image_sha256 && (
            <LTag title={gen.input_image_sha256}>sha256: {gen.input_image_sha256.slice(0, 12)}…</LTag>
          )}
        </LSpace>

        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 4 }}>
            Промпт, по которому сгенерирован этот кадр (prompt_used):
          </div>
          <textarea
            readOnly
            rows={5}
            value={asset.prompt_used || '— промпт не сохранён (старая запись)'}
            style={{
              width: '100%',
              padding: 8,
              fontSize: 13,
              lineHeight: 1.5,
              borderRadius: 6,
              border: '1px solid var(--input-border)',
              background: 'var(--input-bg)',
              color: 'var(--foreground)',
              resize: 'vertical',
            }}
          />
        </div>

        {outdated && currentPrompt && (
          <LAlert
            type="warning"
            showIcon
            style={{ marginTop: 10 }}
            message="Текущий промпт изображения отличается"
            description="Кадр остался утверждённым (автоматически ничего не отменяется), но сгенерирован по прежнему промпту. При необходимости сгенерируйте новый вариант и утвердите его."
          />
        )}
      </div>
    </LModal>
  );
}

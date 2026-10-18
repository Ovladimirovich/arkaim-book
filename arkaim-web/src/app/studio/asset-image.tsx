'use client';

import { LBadge, LSpin, LTag } from '@/shared/ui/light';
import { LoadingOutlined } from '@ant-design/icons';
import { assetFileUrl } from './types';
import type { JobAsset } from './types';

type Props = {
  asset: JobAsset;
  approved?: boolean;
  height?: number;
  /** Открыть в полном размере (просмотр кадра). */
  onOpen?: () => void;
};

export function AssetImage({ asset, approved, height = 160, onOpen }: Props) {
  if (asset.status === 'failed') {
    return (
      <div
        data-testid="asset-image-failed"
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(255,77,79,0.08)',
          borderRadius: 6,
          color: '#cf1322',
          fontSize: 12,
          padding: 8,
          textAlign: 'center',
        }}
      >
        <span title={asset.error || 'причина не указана'}>
          {asset.error || 'ошибка генерации'}
        </span>
      </div>
    );
  }

  if (asset.status !== 'completed' || !asset.file_path) {
    return (
      <div
        data-testid="asset-image-loading"
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--input-bg)',
          borderRadius: 6,
          gap: 8,
        }}
      >
        <LSpin size="small" />
        <LoadingOutlined style={{ color: '#999', fontSize: 12 }} />
        <span style={{ color: '#999', fontSize: 12 }}>генерация…</span>
      </div>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={assetFileUrl(asset.asset_id)}
        alt={asset.title || asset.asset_id}
        onClick={onOpen}
        title={onOpen ? 'Открыть в полный размер' : undefined}
        style={{
          width: '100%',
          height,
          objectFit: 'cover',
          display: 'block',
          borderRadius: 6,
          background: '#111',
          cursor: onOpen ? 'zoom-in' : undefined,
        }}
      />
      {onOpen && (
        <span
          style={{
            position: 'absolute',
            bottom: 6,
            right: 6,
            fontSize: 10,
            padding: '1px 6px',
            borderRadius: 4,
            background: 'rgba(0,0,0,0.55)',
            color: '#fff',
            pointerEvents: 'none',
          }}
        >
          полный размер
        </span>
      )}
      {approved && (
        <LTag
          color="success"
          style={{ position: 'absolute', top: 6, left: 6, fontSize: 10 }}
        >
          <LBadge status="success" /> Утверждено
        </LTag>
      )}
    </div>
  );
}

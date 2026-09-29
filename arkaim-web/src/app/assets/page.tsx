'use client';

import { useState, Suspense, lazy } from 'react';
import { LCard, LTag, LTabs, LEmpty, LSpin, LSpace, LInput, LSelect, LButton, LModal, LBadge, LProgress, toast } from '@/shared/ui/light';
import { PictureOutlined, VideoCameraOutlined, EyeOutlined, ReloadOutlined, DeleteOutlined, CloudDownloadOutlined, ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
const GenerationSettingsPanel = lazy(() => import('@/shared/ui/GenerationSettingsPanel').then(m => ({ default: m.GenerationSettingsPanel })));
const GenerationQueueStatus = lazy(() => import('@/shared/ui/GenerationQueueStatus').then(m => ({ default: m.GenerationQueueStatus })));
import { useGenerationSettings } from '@/shared/contexts/GenerationSettingsContext';

type Asset = {
  asset_id: string;
  asset_type: 'image' | 'video';
  chapter: number;
  scene_id: string;
  title: string;
  mood: string;
  style: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  file_path: string | null;
  prompt_used: string;
  error: string | null;
  created_at: string;
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  generating: 'processing',
  completed: 'success',
  failed: 'error',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  pending: <ClockCircleOutlined />,
  generating: <LoadingOutlined />,
  completed: <CheckCircleOutlined />,
  failed: <CloseCircleOutlined />,
};

function AssetCard({ asset, onDelete, onRegenerate }: {
  asset: Asset;
  onDelete: (id: string) => void;
  onRegenerate: (asset: Asset) => void;
}) {
  const [previewVisible, setPreviewVisible] = useState(false);

  return (
    <LCard hoverable size="small" style={{ height: '100%' }}
      cover={asset.file_path && asset.status === 'completed' ? (
        <div style={{ height: 160, overflow: 'hidden', background: 'var(--divider-color)' }}>
          <img
            src={'/book/assets/' + asset.asset_id + '/file'}
            alt={asset.title}
            style={{ width: '100%', height: 160, objectFit: 'cover' }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        </div>
      ) : (
        <div style={{ height: 160, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface-bg)' }}>
          {asset.asset_type === 'image' ? <PictureOutlined style={{ fontSize: 48, color: '#d9d9d9' }} /> :
           <VideoCameraOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />}
        </div>
      )}
    >
      <div>
        <LSpace style={{ marginBottom: 4 }}>
          <strong style={{ fontSize: 13 }}>{asset.title || asset.scene_id}</strong>
          <LBadge status={STATUS_COLORS[asset.status] as "default" | "processing" | "success" | "error" | "warning"} />
          <LTag color={STATUS_COLORS[asset.status]} style={{ fontSize: 10 }}>
            {asset.status}
          </LTag>
        </LSpace>
        <div style={{ fontSize: 11, color: '#999' }}>
          {asset.asset_type === 'image' ? <PictureOutlined /> : <VideoCameraOutlined />}
          {' '} Глава {asset.chapter} | {asset.mood} | {asset.style}
        </div>
        {asset.error && <div style={{ fontSize: 11, color: '#ef4444' }}>{asset.error}</div>}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        {asset.status === 'completed' && asset.file_path && (
          <LButton type="link" size="small" icon={<EyeOutlined />} onClick={() => setPreviewVisible(true)}>
            Смотреть
          </LButton>
        )}
        <LButton type="link" size="small" icon={<ReloadOutlined />} onClick={() => onRegenerate(asset)}>
          Перегенерировать
        </LButton>
        <LButton type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => { if (confirm('Удалить ассет?')) onDelete(asset.asset_id); }} />
      </div>

      <LModal
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
      >
        <img src={'/book/assets/' + asset.asset_id + '/file'} alt={asset.title} loading="lazy"
          style={{ width: '100%', borderRadius: 8 }} />
        <div style={{ marginTop: 16 }}>
          <div><strong>Промпт:</strong> {asset.prompt_used?.slice(0, 200)}...</div>
          <div><strong>Создан:</strong> {asset.created_at}</div>
        </div>
      </LModal>
    </LCard>
  );
}

function AssetManagerContent() {
  const queryClient = useQueryClient();
  const settings = useGenerationSettings();
  const [filterType, setFilterType] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterChapter, setFilterChapter] = useState<number | undefined>();
  const [generating, setGenerating] = useState(false);
  const [regeneratingAsset, setRegeneratingAsset] = useState<Asset | null>(null);

  const { data: assetsData, isLoading } = useQuery({
    queryKey: ['assets', filterType, filterStatus, filterChapter],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterType) params.set('asset_type', filterType);
      if (filterStatus) params.set('status', filterStatus);
      if (filterChapter) params.set('chapter', String(filterChapter));
      params.set('limit', '100');
      return api.get('/book/assets?' + params.toString());
    },
    refetchInterval: 5000,
  });

  const { data: queueData } = useQuery({
    queryKey: ['queue-status'],
    queryFn: () => api.get('/book/assets/queue/status'),
    staleTime: 3_000,
    refetchInterval: 5_000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete('/book/assets/' + id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      toast.success('Ассет удалён');
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: (asset: Asset) => {
      const params = new URLSearchParams({
        style: settings.style,
        quality: settings.quality,
      });
      return api.post('/book/assets/' + asset.asset_id + '/regenerate?' + params.toString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['queue-status'] });
      toast.success('Перегенерация запущена');
      setRegeneratingAsset(null);
    },
    onError: () => {
      toast.error('Ошибка перегенерации');
      setRegeneratingAsset(null);
    },
  });

  const batchMutation = useMutation({
    mutationFn: () => {
      const params = new URLSearchParams();
      if (filterChapter) params.set('chapter', String(filterChapter));
      params.set('asset_type', filterType || 'image');
      params.set('limit', '20');
      return api.post('/book/assets/batch?' + params.toString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['queue-status'] });
      toast.success('Пакетная генерация запущена');
      setGenerating(false);
    },
  });

  const assets: Asset[] = (assetsData as { data: Asset[] })?.data || [];
  const queueStats = (queueData as { data: { queue_size?: number; running?: number; results_count?: number } })?.data || {};

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 4 }}>Ассеты</h2>
        <span style={{ color: '#999' }}>Управление сгенерированными изображениями и видео</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <PictureOutlined style={{ fontSize: 20, color: '#2563eb' }} />
            <div><strong style={{ fontSize: 18 }}>{assets.filter(a => a.asset_type === 'image').length}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>изображений</span>
          </div>
        </LCard>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <VideoCameraOutlined style={{ fontSize: 20, color: '#7c3aed' }} />
            <div><strong style={{ fontSize: 18 }}>{assets.filter(a => a.asset_type === 'video').length}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>видео</span>
          </div>
        </LCard>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: 20, color: '#10b981' }} />
            <div><strong style={{ fontSize: 18 }}>{assets.filter(a => a.status === 'completed').length}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>готово</span>
          </div>
        </LCard>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <ClockCircleOutlined style={{ fontSize: 20, color: '#f59e0b' }} />
            <div><strong style={{ fontSize: 18 }}>{queueStats.queue_size || 0}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>в очереди</span>
          </div>
        </LCard>
      </div>

      <LSpace style={{ marginBottom: 16 }} wrap>
        <LSelect placeholder="Тип" style={{ width: 120 }} value={filterType} onChange={(v) => setFilterType(v as string)} options={[
          { value: 'image', label: 'Изображения' },
          { value: 'video', label: 'Видео' },
        ].filter(o => o.value)} />
        <LSelect placeholder="Статус" style={{ width: 120 }} value={filterStatus} onChange={(v) => setFilterStatus(v as string)} options={[
          { value: 'completed', label: 'Готово' },
          { value: 'generating', label: 'Генерация' },
          { value: 'failed', label: 'Ошибка' },
          { value: 'pending', label: 'Ожидание' },
        ]} />
        <LSelect placeholder="Глава" style={{ width: 100 }} value={filterChapter !== undefined ? String(filterChapter) : undefined} onChange={(v) => setFilterChapter(v ? Number(v) : undefined)} options={[1,2,3,4,5,6,7,8,9,10].map(ch => ({ value: String(ch), label: `Глава ${ch}` }))} />
        <LButton type="primary" icon={<CloudDownloadOutlined />}
          loading={generating}
          onClick={() => { setGenerating(true); batchMutation.mutate(); }}>
          Пакетная генерация
        </LButton>
      </LSpace>

      <div style={{ marginBottom: 16 }}>
        <Suspense fallback={<LSpin size="small" />}><GenerationQueueStatus compact /></Suspense>
      </div>

      <LModal
        title="Перегенерировать ассет"
        open={!!regeneratingAsset}
        onCancel={() => setRegeneratingAsset(null)}
        footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <LButton onClick={() => setRegeneratingAsset(null)}>Отмена</LButton>
          <LButton type="primary" loading={regenerateMutation.isPending} onClick={() => regeneratingAsset && regenerateMutation.mutate(regeneratingAsset)}>Сгенерировать</LButton>
        </div>}
      >
        {regeneratingAsset && (
          <div>
            <strong>{regeneratingAsset.title || regeneratingAsset.scene_id}</strong>
            <span style={{ display: 'block', marginBottom: 16, color: '#999' }}>
              Глава {regeneratingAsset.chapter} | {regeneratingAsset.mood} | {regeneratingAsset.style}
            </span>
            <Suspense fallback={<LSpin size="small" />}><GenerationSettingsPanel compact /></Suspense>
          </div>
        )}
      </LModal>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>
      ) : assets.length === 0 ? (
        <LEmpty description="Ассеты не найдены. Нажмите «Пакетная генерация» или сгенерируйте через Визуал." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 12 }}>
          {assets.map(asset => (
            <AssetCard
              key={asset.asset_id}
              asset={asset}
              onDelete={(id) => deleteMutation.mutate(id)}
              onRegenerate={(a) => setRegeneratingAsset(a)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function AssetsPage() {
  return (
    <ProtectedRoute>
      <AssetManagerContent />
    </ProtectedRoute>
  );
}
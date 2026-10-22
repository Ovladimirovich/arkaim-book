'use client';

import { useState } from 'react';
import { LCard, LTag, LEmpty, LSpin, LSpace, LSelect, LButton, LModal, LBadge, toast } from '@/shared/ui/light';
import { PictureOutlined, VideoCameraOutlined, EyeOutlined, DeleteOutlined, ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, InfoCircleOutlined, GlobalOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';

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
  // Provenance выполнения (ADR_MEDIA_PLAN_V0): какой backend/план дали результат.
  generation?: {
    plan_id?: string | null;
    backend?: string | null;
    workflow_used?: string | null;
    media_id?: string | null;
    shot_id?: string | null;
  };
};

type WorldLink = {
  link_type: string;
  status: string;
  target_kind: string;
  target_id: string;
  target_label: string;
  basis?: string;
};

const WORLD_STATUS_COLORS: Record<string, string> = {
  CONFIRMED: 'success',
  DERIVED: 'processing',
  UNRESOLVED: 'warning',
  AMBIGUOUS: 'purple',
};

// target_kind, которые открываются как сущность мира в /world-engine
const WORLD_ENTITY_KINDS = ['world_location', 'world_event', 'world_character'];

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

function AssetCard({ asset, onDelete }: {
  asset: Asset;
  onDelete: (id: string) => void;
}) {
  const [previewVisible, setPreviewVisible] = useState(false);
  // Provenance: asset → сцена (глава, scene_id) → сущности мира
  const [worldModalOpen, setWorldModalOpen] = useState(false);
  const [worldLinks, setWorldLinks] = useState<WorldLink[] | null>(null);
  const [worldLinksLoading, setWorldLinksLoading] = useState(false);

  const loadWorldLinks = async () => {
    setWorldModalOpen(true);
    if (worldLinks !== null) return;
    setWorldLinksLoading(true);
    try {
      const res = await api.get<{ data: { links: WorldLink[] } }>(
        `/studio/scenes/${encodeURIComponent(asset.scene_id)}/world-links`
      );
      setWorldLinks(res.data?.links ?? []);
    } catch {
      setWorldLinks([]);
    }
    setWorldLinksLoading(false);
  };

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
        {asset.scene_id && (
          <div style={{ fontSize: 11, color: '#999' }}>
            Сцена: {asset.scene_id}
          </div>
        )}
        {asset.generation?.backend && (
          <div style={{ fontSize: 11, color: '#999' }}>
            Media: {asset.generation.backend}
            {asset.generation.media_id ? ` · ${asset.generation.media_id}` : ''}
            {asset.generation.shot_id ? ` · шот ${asset.generation.shot_id}` : ''}
          </div>
        )}
        {asset.error && <div style={{ fontSize: 11, color: '#ef4444' }}>{asset.error}</div>}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        {asset.status === 'completed' && asset.file_path && (
          <LButton type="link" size="small" icon={<EyeOutlined />} onClick={() => setPreviewVisible(true)}>
            Смотреть
          </LButton>
        )}
        {asset.scene_id && (
          <LButton type="link" size="small" icon={<GlobalOutlined />} onClick={loadWorldLinks}>
            Мир
          </LButton>
        )}
        <LButton type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => { if (confirm('Удалить ассет?')) onDelete(asset.asset_id); }} />
      </div>

      <LModal
        open={worldModalOpen}
        onCancel={() => setWorldModalOpen(false)}
        footer={null}
        width={640}
        title={`Связи сцены ${asset.scene_id} с миром`}
      >
        {worldLinksLoading ? <LSpin /> : !worldLinks || worldLinks.length === 0 ? (
          <LEmpty description="Связи с миром для этой сцены не найдены" />
        ) : (
          <div>
            {worldLinks.map((link, i) => (
              <div key={i} style={{ padding: 8, borderBottom: '1px solid #f0f0f0' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: 13 }}>{link.target_label || link.target_id || '—'}</strong>
                  <LTag style={{ fontSize: 10 }}>{link.target_kind}</LTag>
                  <LTag color={WORLD_STATUS_COLORS[link.status] || 'default'} style={{ fontSize: 10 }}>{link.status}</LTag>
                  {WORLD_ENTITY_KINDS.includes(link.target_kind) && link.target_id && (
                    <a
                      href={`/world-engine?entity_id=${encodeURIComponent(link.target_id)}`}
                      style={{ fontSize: 12, color: '#1677ff' }}
                    >
                      в World Engine
                    </a>
                  )}
                </div>
                {link.basis && <div style={{ fontSize: 11, color: '#666' }}>{link.basis}</div>}
              </div>
            ))}
          </div>
        )}
      </LModal>

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
  const [filterType, setFilterType] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterChapter, setFilterChapter] = useState<number | undefined>();

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

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete('/book/assets/' + id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      toast.success('Ассет удалён');
    },
  });

  const assets: Asset[] = (assetsData as { data: Asset[] })?.data || [];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 4 }}>Ассеты</h2>
        <span style={{ color: '#999' }}>Просмотр и управление изображениями и видео</span>
      </div>

      <div style={{ marginBottom: 16 }}>
        <LCard size="small">
          <LSpace>
            <InfoCircleOutlined style={{ color: '#2563eb', marginTop: 3 }} />
            <span style={{ fontSize: 12, color: '#666' }}>
              Генерация изображений и видео перенесена в отдельный сервис <strong>arkaim-media</strong>.
              Arkaim формирует смысловой запрос (MediaPlan), а исполнение выполняет arkaim-media.
              Здесь доступны только просмотр и удаление.
            </span>
          </LSpace>
        </LCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
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
      </LSpace>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>
      ) : assets.length === 0 ? (
        <LEmpty description="Ассеты не найдены." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 12 }}>
          {assets.map(asset => (
            <AssetCard
              key={asset.asset_id}
              asset={asset}
              onDelete={(id) => deleteMutation.mutate(id)}
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
'use client';

import { useState, Suspense, lazy } from 'react';
import { LCard, LTag, LButton, LSpace, LInput, LModal, LForm, useLForm, LSelect, LInputNumber, LDivider, LEmpty, LSpin, LBadge, LDrawer, LProgress, LTextArea, toast } from '@/shared/ui/light';
import {
  PlusOutlined, DeleteOutlined, PlayCircleOutlined,
  CameraOutlined, EyeOutlined, EditOutlined, CopyOutlined,
  CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
  LoadingOutlined, ThunderboltOutlined, VideoCameraOutlined, PictureOutlined,
  SettingOutlined, HistoryOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { useGenerationSettings } from '@/shared/contexts/GenerationSettingsContext';
const GenerationSettingsPanel = lazy(() => import('@/shared/ui/GenerationSettingsPanel').then(m => ({ default: m.GenerationSettingsPanel })));

// ── Types ──────────────────────────────────────────────

type ShotVersion = {
  id: string;
  asset_id: string | null;
  prompt: string;
  camera: { shot_type: string; angle: string; motion: string };
  duration_sec: number;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  error: string | null;
  is_active: boolean;
  quality: string;
  created_at: string;
};

type SceneShot = {
  id: string;
  scene_id: string;
  order: number;
  prompt_override: string;
  camera: { shot_type: string; angle: string; motion: string };
  duration_sec: number;
  versions: ShotVersion[];
};

type FilmProject = {
  id: string;
  title: string;
  description: string;
  status: string;
  style: string;
  mood: string;
  aspect_ratio: string;
  fps: number;
  scenes: SceneShot[];
  output_path: string | null;
  created_at: string;
};

type ProjectSummary = {
  id: string;
  title: string;
  status: string;
  scene_count: number;
  shot_count: number;
  completed_shots: number;
  total_duration_sec: number;
  created_at: string;
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', generating: 'processing', assembling: 'warning',
  complete: 'success', failed: 'error', pending: 'default',
  completed: 'success',
};

const CAMERA_MOTIONS = [
  { value: 'static', label: 'Статическая' },
  { value: 'slow_dolly_in', label: 'Dolly In' },
  { value: 'slow_dolly_out', label: 'Dolly Out' },
  { value: 'slow_pan', label: 'Pan' },
  { value: 'slow_zoom_in', label: 'Zoom In' },
  { value: 'slow_zoom_out', label: 'Zoom Out' },
  { value: 'tracking', label: 'Tracking' },
  { value: 'crane_up', label: 'Crane Up' },
  { value: 'orbit', label: 'Orbit' },
  { value: 'follow', label: 'Follow' },
];

// ── Project List ───────────────────────────────────────

function ProjectList({ onSelect, onCreate }: { onSelect: (id: string) => void; onCreate: () => void }) {
  const { data, isLoading } = useQuery<{ data: ProjectSummary[] }>({
    queryKey: ['film-projects'],
    queryFn: () => api.get('/book/film/list'),
    refetchInterval: 5000,
  });

  const projects: ProjectSummary[] = data?.data || [];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h4 style={{ margin: 0 }}>Проекты фильмов</h4>
        <LButton type="primary" icon={<PlusOutlined />} onClick={onCreate}>
          Новый проект
        </LButton>
      </div>

      {isLoading ? (
        <LSpin />
      ) : projects.length === 0 ? (
        <LEmpty description="Нет проектов. Создайте первый!" />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {projects.map(p => (
            <LCard
              hoverable
              size="small"
              key={p.id}
              onClick={() => onSelect(p.id)}
              style={{ cursor: 'pointer' }}
            >
              <div style={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>{p.title}</strong>
                  <LBadge status={STATUS_COLORS[p.status] as "default" | "processing" | "success" | "error" | "warning"}
                    text={<LTag color={STATUS_COLORS[p.status]} style={{ fontSize: 10 }}>{p.status}</LTag>} />
                </div>
                <LSpace size={12}>
                  <span style={{ fontSize: 11, color: '#999' }}>
                    <VideoCameraOutlined /> {p.scene_count} сцен
                  </span>
                  <span style={{ fontSize: 11, color: '#999' }}>
                    <PictureOutlined /> {p.completed_shots}/{p.shot_count} шотов
                  </span>
                  <span style={{ fontSize: 11, color: '#999' }}>
                    <ClockCircleOutlined /> {p.total_duration_sec.toFixed(1)}с
                  </span>
                </LSpace>
                {p.shot_count > 0 && (
                  <LProgress
                    percent={Math.round((p.completed_shots / p.shot_count) * 100)}
                    size="small"
                    status={p.status === 'failed' ? 'exception' : 'active'}
                  />
                )}
              </div>
            </LCard>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Shot Editor Drawer ─────────────────────────────

function ShotEditor({
  shot, allVersions, sceneId, projectId, onClose
}: {
  shot: ShotVersion | null;
  allVersions: ShotVersion[];
  sceneId: string;
  projectId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { style, mood, quality } = useGenerationSettings();
  const [panelCollapsed, setPanelCollapsed] = useState(true);

  const generateMutation = useMutation({
    mutationFn: () => {
      const params = new URLSearchParams();
      if (style) params.append('style', style);
      if (mood) params.append('mood', mood);
      if (quality) params.append('quality', quality);
      const qs = params.toString();
      return api.post(
        `/book/film/${projectId}/scenes/${sceneId}/shots/${shot?.id}/generate` +
        (qs ? '?' + qs : '')
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['film-project', projectId] });
      toast.success('Шот сгенерирован');
    },
    onError: () => toast.error('Ошибка генерации'),
  });

  const activateMutation = useMutation({
    mutationFn: (shotId: string) => api.put(`/book/film/shots/${shotId}/activate`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['film-project', projectId] });
      toast.success('Версия активирована');
    },
    onError: () => toast.error('Ошибка активации'),
  });

  const newVersionMutation = useMutation({
    mutationFn: () => api.post(
      `/book/film/${projectId}/scenes/${sceneId}/shots/new-version` +
      `?prompt=${encodeURIComponent(shot?.prompt || '')}` +
      `&duration_sec=${shot?.duration_sec || 3}`
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['film-project', projectId] });
      toast.success('Новая версия создана');
    },
    onError: () => toast.error('Ошибка создания версии'),
  });

  const deleteMutation = useMutation({
    mutationFn: (shotId: string) => api.delete(`/book/film/shots/${shotId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['film-project', projectId] });
      toast.success('Шот удалён');
      onClose();
    },
    onError: () => toast.error('Ошибка удаления'),
  });

  if (!shot) return null;

  const assetUrl = shot.asset_id ? `/book/assets/${shot.asset_id}/file` : null;

  return (
    <LDrawer
      title={`Шот: ${shot.id.slice(0, 12)}...`}
      open={!!shot}
      onClose={onClose}
      width={540}
      extra={
        <LSpace>
          <LButton
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={generateMutation.isPending}
            onClick={() => generateMutation.mutate()}
          >
            Сгенерировать
          </LButton>
          <LButton danger icon={<DeleteOutlined />} onClick={() => { if (confirm('Удалить шот?')) deleteMutation.mutate(shot.id); }} />
        </LSpace>
      }
    >
      {assetUrl && (
        <div style={{ textAlign: 'center', marginBottom: 16, background: 'var(--divider-color)', borderRadius: 8, padding: 8 }}>
          <img
            src={assetUrl}
            alt="Shot preview"
            style={{ maxWidth: '100%', maxHeight: 300, borderRadius: 4 }}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        </div>
      )}

      <LCard
        size="small"
        style={{ marginBottom: 16 }}
        title={
          <LSpace>
            <SettingOutlined style={{ color: '#faad14' }} />
            <strong>Настройки генерации</strong>
          </LSpace>
        }
        extra={
          <LButton size="small" onClick={() => setPanelCollapsed(!panelCollapsed)}>
            {panelCollapsed ? 'Настройки' : 'Скрыть'}
          </LButton>
        }
      >
        {!panelCollapsed && <Suspense fallback={<LSpin size="small" />}><GenerationSettingsPanel compact /></Suspense>}
        <LSpace style={{ marginTop: panelCollapsed ? 0 : 8 }}>
          <span style={{ fontSize: 12, color: '#999' }}>
            Стиль: {style} | Настроение: {mood} | Качество: {quality}
          </span>
        </LSpace>
      </LCard>

      <div style={{ marginBottom: 16 }}>
        <LSpace>
          <LBadge status={STATUS_COLORS[shot.status] as "default" | "processing" | "success" | "error" | "warning"} />
          <strong>Статус: {shot.status}</strong>
          {shot.quality && shot.quality !== 'standard' && (
            <LTag color={shot.quality === 'ultra' ? 'gold' : shot.quality === 'high' ? 'blue' : 'default'}>
              {shot.quality}
            </LTag>
          )}
        </LSpace>
        {shot.error && <span style={{ display: 'block', marginTop: 4, color: '#ef4444' }}>{shot.error}</span>}
      </div>

      <LCard size="small" title="Камера" style={{ marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <div><strong>Тип:</strong> {shot.camera?.shot_type || 'medium_shot'}</div>
          <div><strong>Угол:</strong> {shot.camera?.angle || 'eye_level'}</div>
          <div><strong>Движение:</strong> {shot.camera?.motion || 'static'}</div>
          <div><strong>Длительность:</strong> {shot.duration_sec}с</div>
        </div>
      </LCard>

      <LCard size="small" title="Промпт" style={{ marginBottom: 16 }}>
        <p style={{ margin: 0, fontSize: 12 }}>{shot.prompt || '—'}</p>
      </LCard>

      <LCard
        size="small"
        title={<LSpace><HistoryOutlined /> Версии ({allVersions.length})</LSpace>}
        extra={
          <LButton size="small" icon={<CopyOutlined />} onClick={() => newVersionMutation.mutate()}>
            Новая версия
          </LButton>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {allVersions.map((v, idx) => (
            <div key={v.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingLeft: 12, borderLeft: `3px solid ${v.is_active ? '#52c41a' : '#d9d9d9'}` }}>
              <LSpace>
                <strong style={{ fontWeight: v.is_active ? 700 : 400 }}>v{idx + 1}</strong>
                {v.is_active && <LTag color="green">активная</LTag>}
                <LBadge status={STATUS_COLORS[v.status] as "default" | "processing" | "success" | "error" | "warning"} />
                <span style={{ fontSize: 11, color: '#999' }}>{v.created_at}</span>
              </LSpace>
              <LSpace size={4}>
                {v.asset_id && (
                  <a href={`/book/assets/${v.asset_id}/file`} target="_blank"
                    style={{ fontSize: 12, color: '#2563eb' }} title="Превью">
                    <EyeOutlined />
                  </a>
                )}
                {!v.is_active && v.status === 'completed' && (
                  <LButton
                    size="small"
                    type="link"
                    icon={<CheckCircleOutlined />}
                    onClick={() => activateMutation.mutate(v.id)}
                  >
                    Активировать
                  </LButton>
                )}
                <LButton size="small" type="link" danger icon={<DeleteOutlined />} onClick={() => { if (confirm('Удалить версию?')) deleteMutation.mutate(v.id); }} />
              </LSpace>
            </div>
          ))}
        </div>
      </LCard>
    </LDrawer>
  );
}

// ── Project Editor ─────────────────────────────────────

function ProjectEditor({ projectId, onBack }: { projectId: string; onBack: () => void }) {
  const queryClient = useQueryClient();
  const [selectedShot, setSelectedShot] = useState<ShotVersion | null>(null);
  const [selectedSceneId, setSelectedSceneId] = useState<string>('');
  const [addSceneVisible, setAddSceneVisible] = useState(false);
  const [addShotVisible, setAddShotVisible] = useState(false);
  const [newSceneId, setNewSceneId] = useState('');
  const [newShotPrompt, setNewShotPrompt] = useState('');
  const [newShotDuration, setNewShotDuration] = useState(3);
  const [newShotMotion, setNewShotMotion] = useState('static');

  const { data, isLoading } = useQuery({
    queryKey: ['film-project', projectId],
    queryFn: () => api.get(`/book/film/${projectId}`),
    refetchInterval: 3000,
  });

  const project: FilmProject | null = (data as { data: FilmProject })?.data || null;

  const addSceneMutation = useMutation({
    mutationFn: () => api.post(`/book/film/${projectId}/scenes?scene_id=${newSceneId}&duration_sec=5`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['film-project', projectId] });
      setAddSceneVisible(false);
      setNewSceneId('');
      toast.success('Сцена добавлена');
    },
    onError: () => toast.error('Ошибка добавления сцены'),
  });

  const addShotMutation = useMutation({
    mutationFn: () => api.post(
      `/book/film/${projectId}/scenes/${selectedSceneId}/shots` +
      `?prompt=${encodeURIComponent(newShotPrompt)}` +
      `&duration_sec=${newShotDuration}` +
      `&camera_motion=${newShotMotion}`
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['film-project', projectId] });
      setAddShotVisible(false);
      setNewShotPrompt('');
      toast.success('Шот добавлен');
    },
    onError: () => toast.error('Ошибка добавления шота'),
  });

  const deleteSceneMutation = useMutation({
    mutationFn: (sceneId: string) => api.delete(`/book/film/${projectId}/scenes/${sceneId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['film-project', projectId] });
      toast.success('Сцена удалена');
    },
    onError: () => toast.error('Ошибка удаления сцены'),
  });

  const deleteProjectMutation = useMutation({
    mutationFn: () => api.delete(`/book/film/${projectId}`),
    onSuccess: () => {
      toast.success('Проект удалён');
      onBack();
    },
    onError: () => toast.error('Ошибка удаления проекта'),
  });

  const { data: assembleStatusData } = useQuery({
    queryKey: ['film-assemble-status', projectId],
    queryFn: () => api.get(`/book/film/${projectId}/assemble/status`),
    staleTime: 2_000,
    refetchInterval: (query: any) => {
      const status = query.state.data?.data?.status;
      return status === 'assembling' || status === 'preparing' ? 2000 : false;
    },
  });

  const assembleStatus = (assembleStatusData as { data?: { status?: string; shot_count?: number; duration_sec?: number; error?: string; output_path?: string } })?.data;

  if (isLoading) return <LSpin />;
  if (!project) return <LEmpty description="Проект не найден" />;

  const totalShots = project.scenes.reduce((sum, s) => sum + s.versions.length, 0);
  const completedShots = project.scenes.reduce(
    (sum, s) => sum + s.versions.filter((v: ShotVersion) => v.status === 'completed').length, 0
  );
  const activeDuration = project.scenes.reduce(
    (sum, s) => sum + s.versions
      .filter((v: ShotVersion) => v.is_active && v.status === 'completed')
      .reduce((vs: number, v: ShotVersion) => vs + v.duration_sec, 0), 0
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <LSpace>
          <LButton onClick={onBack}>← Назад</LButton>
          <h4 style={{ margin: 0 }}>{project.title}</h4>
          <LBadge status={STATUS_COLORS[project.status] as "default" | "processing" | "success" | "error" | "warning"}
            text={<LTag color={STATUS_COLORS[project.status]}>{project.status}</LTag>} />
        </LSpace>
        <LSpace>
          <LButton danger icon={<DeleteOutlined />} onClick={() => { if (confirm('Удалить проект?')) deleteProjectMutation.mutate(); }}>Удалить</LButton>
        </LSpace>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <VideoCameraOutlined style={{ fontSize: 20, color: '#2563eb' }} />
            <div><strong style={{ fontSize: 18 }}>{project.scenes.length}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>сцен</span>
          </div>
        </LCard>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <PictureOutlined style={{ fontSize: 20, color: '#7c3aed' }} />
            <div><strong style={{ fontSize: 18 }}>{completedShots}/{totalShots}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>шотов</span>
          </div>
        </LCard>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <ClockCircleOutlined style={{ fontSize: 20, color: '#10b981' }} />
            <div><strong style={{ fontSize: 18 }}>{activeDuration.toFixed(1)}с</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>длительность</span>
          </div>
        </LCard>
        <LCard size="small">
          <div style={{ textAlign: 'center' }}>
            <CheckCircleOutlined style={{ fontSize: 20, color: '#f59e0b' }} />
            <div><strong style={{ fontSize: 18 }}>{totalShots > 0 ? Math.round((completedShots / totalShots) * 100) : 0}%</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>готовность</span>
          </div>
        </LCard>
      </div>

      {assembleStatus && assembleStatus.status !== 'idle' && (
        <LCard size="small" style={{ marginBottom: 16 }}>
          <LSpace>
            {assembleStatus.status === 'assembling' || assembleStatus.status === 'preparing' ? (
              <LoadingOutlined style={{ color: '#1890ff' }} />
            ) : assembleStatus.status === 'complete' ? (
              <CheckCircleOutlined style={{ color: '#52c41a' }} />
            ) : (
              <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
            )}
            <span>
              {"Сборка: "}
              <LTag color={assembleStatus.status === 'complete' ? 'success' : assembleStatus.status === 'failed' ? 'error' : 'processing'}>
                {assembleStatus.status}
              </LTag>
              {(assembleStatus.shot_count ?? 0) > 0 && ` ${assembleStatus.shot_count} шотов`}
              {(assembleStatus.duration_sec ?? 0) > 0 && ` / ${assembleStatus.duration_sec?.toFixed(1)}с`}
            </span>
            {assembleStatus.error && <span style={{ color: '#ef4444' }}> - {assembleStatus.error}</span>}
            {assembleStatus.status === 'complete' && assembleStatus.output_path && (
              <LButton size="small" icon={<PlayCircleOutlined />} href="/api/film/output" target="_blank">
                {"Смотреть"}
              </LButton>
            )}
          </LSpace>
        </LCard>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h5 style={{ margin: 0 }}>Сцены и шоты</h5>
        <LButton icon={<PlusOutlined />} onClick={() => setAddSceneVisible(true)}>
          Добавить сцену
        </LButton>
      </div>

      {project.scenes.length === 0 ? (
        <LEmpty description="Добавьте сцену из генома книги" />
      ) : (
        project.scenes.map(scene => (
          <LCard
            key={scene.id}
            size="small"
            style={{ marginBottom: 12 }}
            title={
              <LSpace>
                <VideoCameraOutlined />
                <strong>{scene.scene_id}</strong>
                <LTag>Порядок: {scene.order}</LTag>
                <LTag>{scene.versions.length} шотов</LTag>
              </LSpace>
            }
            extra={
              <LSpace>
                <LButton size="small" icon={<PlusOutlined />} onClick={() => {
                  setSelectedSceneId(scene.id);
                  setAddShotVisible(true);
                }}>
                  Шот
                </LButton>
                <LButton size="small" danger icon={<DeleteOutlined />} onClick={() => { if (confirm('Удалить сцену?')) deleteSceneMutation.mutate(scene.id); }} />
              </LSpace>
            }
          >
            {scene.versions.length === 0 ? (
              <LEmpty description="Нет шотов. Добавьте первый!" />
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 8 }}>
                {scene.versions.map(shot => (
                  <LCard
                    key={shot.id}
                    size="small"
                    hoverable
                    onClick={() => {
                      setSelectedSceneId(scene.id);
                      setSelectedShot(shot);
                    }}
                    style={{
                      border: shot.is_active ? '2px solid #52c41a' : '1px solid #d9d9d9',
                      cursor: 'pointer',
                    }}
                  >
                    {shot.asset_id ? (
                      <div style={{ height: 80, overflow: 'hidden', background: 'var(--divider-color)', borderRadius: 4, marginBottom: 4 }}>
                        <img
                          src={`/book/assets/${shot.asset_id}/file`}
                          alt=""
                          style={{ width: '100%', height: 80, objectFit: 'cover' }}
                          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                        />
                      </div>
                    ) : (
                      <div style={{ height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface-bg)', borderRadius: 4, marginBottom: 4 }}>
                        <PictureOutlined style={{ fontSize: 24, color: '#d9d9d9' }} />
                      </div>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <LBadge status={STATUS_COLORS[shot.status] as "default" | "processing" | "success" | "error" | "warning"} />
                      <span style={{ fontSize: 10, color: '#999' }}>{shot.duration_sec}с</span>
                    </div>
                    {shot.is_active && <LTag color="green" style={{ fontSize: 9, marginTop: 4 }}>активная</LTag>}
                    {shot.quality && shot.quality !== 'standard' && (
                      <LTag color={shot.quality === 'ultra' ? 'gold' : shot.quality === 'high' ? 'blue' : 'default'} style={{ fontSize: 9 }}>
                        {shot.quality}
                      </LTag>
                    )}
                  </LCard>
                ))}
              </div>
            )}
          </LCard>
        ))
      )}

      <LModal
        title="Добавить сцену"
        open={addSceneVisible}
        onCancel={() => setAddSceneVisible(false)}
        footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <LButton onClick={() => setAddSceneVisible(false)}>Отмена</LButton>
          <LButton type="primary" loading={addSceneMutation.isPending} onClick={() => addSceneMutation.mutate()}>Добавить</LButton>
        </div>}
      >
        <LForm layout="vertical">
          <LForm.Item label="Scene ID из генома">
            <LInput
              value={newSceneId}
              onChange={e => setNewSceneId(e.target.value)}
              placeholder="scene_001"
            />
          </LForm.Item>
        </LForm>
      </LModal>

      <LModal
        title="Добавить шот"
        open={addShotVisible}
        onCancel={() => setAddShotVisible(false)}
        footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <LButton onClick={() => setAddShotVisible(false)}>Отмена</LButton>
          <LButton type="primary" loading={addShotMutation.isPending} onClick={() => addShotMutation.mutate()}>Добавить</LButton>
        </div>}
      >
        <LForm layout="vertical">
          <LForm.Item label="Промпт">
            <LTextArea
              value={newShotPrompt}
              onChange={e => setNewShotPrompt(e.target.value)}
              placeholder="epic fantasy scene, ancient temple..."
              rows={3}
            />
          </LForm.Item>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <LForm.Item label="Длительность (сек)">
              <LInputNumber
                value={newShotDuration}
                onChange={v => setNewShotDuration(v || 3)}
                min={0.5} max={30} step={0.5}
                style={{ width: '100%' }}
              />
            </LForm.Item>
            <LForm.Item label="Движение камеры">
              <LSelect
                value={newShotMotion}
                onChange={setNewShotMotion}
                options={CAMERA_MOTIONS}
              />
            </LForm.Item>
          </div>
        </LForm>
      </LModal>

      <ShotEditor
        shot={selectedShot}
        allVersions={selectedShot ? project.scenes.find(s => s.id === selectedSceneId)?.versions || [] : []}
        sceneId={selectedSceneId}
        projectId={projectId}
        onClose={() => setSelectedShot(null)}
      />
    </div>
  );
}

// ── Create Project Modal ───────────────────────────────

function CreateProjectModal({ visible, onClose }: { visible: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, formRef] = useLForm();
  const [loading, setLoading] = useState(false);
  const { style, mood } = useGenerationSettings();

  const handleCreate = async () => {
    try {
      const values: any = await form.validateFields();
      setLoading(true);
      const params = new URLSearchParams({
        title: values.title,
        description: values.description || '',
        style: values.style || 'cinematic_fantasy',
        mood: values.mood || 'neutral',
        aspect_ratio: values.aspect_ratio || '16:9',
        fps: String(values.fps || 24),
      });
      await api.post('/book/film/create?' + params.toString());
      queryClient.invalidateQueries({ queryKey: ['film-projects'] });
      toast.success('Проект создан');
      form.resetFields();
      onClose();
    } catch (e) {
      // validation error
    } finally {
      setLoading(false);
    }
  };

  return (
    <LModal
      title="Новый проект фильма"
      open={visible}
      onCancel={onClose}
      footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <LButton onClick={onClose}>Отмена</LButton>
        <LButton type="primary" loading={loading} onClick={handleCreate}>Создать</LButton>
      </div>}
    >
      <LForm
        ref={formRef}
        layout="vertical"
        initialValues={{
          style: style,
          mood: mood,
          aspect_ratio: '16:9',
          fps: 24,
        }}
      >
        <LForm.Item name="title" label="Название" rules={[{ required: true }]}>
          <LInput placeholder="Arkaim Episode 1" />
        </LForm.Item>
        <LForm.Item name="description" label="Описание">
          <LTextArea rows={2} placeholder="Описание проекта..." />
        </LForm.Item>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <LForm.Item name="style" label="Стиль">
            <LSelect options={[
              { value: 'cinematic_fantasy', label: 'Cinematic Fantasy' },
              { value: 'realistic', label: 'Realistic' },
              { value: 'watercolor', label: 'Watercolor' },
              { value: 'dark_gothic', label: 'Dark Gothic' },
              { value: 'ethereal', label: 'Ethereal' },
              { value: 'oil_painting', label: 'Oil Painting' },
            ]} />
          </LForm.Item>
          <LForm.Item name="mood" label="Настроение">
            <LSelect options={[
              { value: 'neutral', label: 'Neutral' },
              { value: 'dark_mystical', label: 'Dark Mystical' },
              { value: 'warm_intimate', label: 'Warm Intimate' },
              { value: 'hopeful_golden', label: 'Hopeful Golden' },
              { value: 'dramatic_contrast', label: 'Dramatic' },
              { value: 'ethereal_light', label: 'Ethereal' },
            ]} />
          </LForm.Item>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <LForm.Item name="aspect_ratio" label="Соотношение">
            <LSelect options={[
              { value: '16:9', label: '16:9' },
              { value: '1:1', label: '1:1' },
              { value: '9:16', label: '9:16' },
            ]} />
          </LForm.Item>
          <LForm.Item name="fps" label="FPS">
            <LSelect options={[
              { value: '12', label: '12' },
              { value: '24', label: '24' },
              { value: '30', label: '30' },
              { value: '60', label: '60' },
            ]} />
          </LForm.Item>
        </div>
      </LForm>
    </LModal>
  );
}

// ── Main Page ──────────────────────────────────────────

function FilmStudioContent() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [createVisible, setCreateVisible] = useState(false);

  if (selectedProjectId) {
    return (
      <ProjectEditor
        projectId={selectedProjectId}
        onBack={() => setSelectedProjectId(null)}
      />
    );
  }

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 4 }}>
          <VideoCameraOutlined style={{ marginRight: 8 }} />
          Film Studio
        </h2>
        <span style={{ color: '#999' }}>Создавайте фильмы из сцен книги «Наследие Аркаима»</span>
      </div>

      <ProjectList
        onSelect={setSelectedProjectId}
        onCreate={() => setCreateVisible(true)}
      />

      <CreateProjectModal
        visible={createVisible}
        onClose={() => setCreateVisible(false)}
      />
    </>
  );
}

export default function FilmStudioPage() {
  return (
    <ProtectedRoute>
      <FilmStudioContent />
    </ProtectedRoute>
  );
}
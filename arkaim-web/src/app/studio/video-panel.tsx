'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LAlert,
  LBadge,
  LButton,
  LCard,
  LEmpty,
  LSelect,
  LSpace,
  LSpin,
  LTag,
  toast,
} from '@/shared/ui/light';
import {
  LoadingOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { AssetImage } from './asset-image';
import { isMockGeneration, videoKindLabel, videoOutdatedReasons } from './staleness';
import {
  STATUS_COLORS,
  STATUS_LABELS,
  VIDEO_EXECUTORS,
  VIDEO_SIZES,
  assetFileUrl,
  unwrapData,
} from './types';
import type { JobAsset, MediaPlanT, Scene } from './types';

type Props = {
  scene: Scene;
  videoPlan: MediaPlanT | null;
  imageAssetId?: string | null;
};

function JobStatusPanel({
  job,
  loading,
  approvedImageAssetId,
  referenceImage,
  currentFullPrompt,
}: {
  job?: JobAsset;
  loading: boolean;
  approvedImageAssetId?: string | null;
  referenceImage?: JobAsset;
  currentFullPrompt: string;
}) {
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12 }}>
        <LSpin size="small" /> <span style={{ color: '#999' }}>Загрузка состояния задания…</span>
      </div>
    );
  }
  if (!job) {
    return (
      <LEmpty description="Задание не запущено. Утвердите кадр и нажмите «Создать видео»." />
    );
  }
  if (job.status === 'pending' || job.status === 'generating') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 12 }}>
        <LSpin size="small" />
        <LBadge status="processing" />
        <strong>Задание выполняется…</strong>
        <span style={{ color: '#999', fontSize: 12 }}>
          статус обновляется автоматически; видео появится здесь после завершения
        </span>
      </div>
    );
  }
  if (job.status === 'failed') {
    return (
      <LAlert
        type="error"
        showIcon
        message="Задание завершилось ошибкой"
        description={
          <div>
            <div style={{ fontFamily: 'monospace' }}>{job.error || 'причина не указана'}</div>
            <div style={{ marginTop: 6, fontSize: 12 }}>
              {job.error?.startsWith('input_image_read_failed')
                ? 'Утверждённый кадр не удалось прочитать — видео НЕ создано (запуск без кадра запрещён). Проверьте изображение во вкладке «Изображение».'
                : 'Задание можно запустить заново после исправления (например, выберите исполнителя mock).'}
            </div>
          </div>
        }
      />
    );
  }
  const gen = job.generation || {};
  const transmitted = !!gen.reference_image_id;
  const withoutApprovedFrame = !!approvedImageAssetId && !transmitted;
  const mock = isMockGeneration(job);
  const outdatedReasons = videoOutdatedReasons(job, {
    approvedImageAssetId,
    currentFullPrompt,
  });
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <LBadge status="success" />
        <strong>Видео готово</strong>
        <LTag color="success">{job.asset_id}</LTag>
        <LTag color={mock ? 'orange' : 'green'} style={{ fontSize: 11 }}>
          {videoKindLabel(job)}
        </LTag>
      </div>
      <video
        controls
        preload="metadata"
        src={assetFileUrl(job.asset_id)}
        style={{ width: '100%', maxHeight: 420, borderRadius: 8, background: '#000' }}
      />
      {referenceImage && (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginTop: 8 }}>
          <div style={{ width: 120 }}>
            <AssetImage asset={referenceImage} height={68} />
          </div>
          <div style={{ fontSize: 12 }}>
            <div>
              <strong>Исходный кадр этого видео</strong>
            </div>
            <div style={{ color: '#999' }}>
              {transmitted
                ? `передан исполнителю: ${gen.reference_image_id}`
                : 'кадр исполнителю не передавался'}
            </div>
          </div>
        </div>
      )}
      {withoutApprovedFrame && (
        <LAlert
          type="warning"
          showIcon
          style={{ marginTop: 8 }}
          message="Визуальная связь не гарантирована"
          description="Утверждённый кадр сессии НЕ передавался исполнителю этого видео (video-jobs запущен без него)."
        />
      )}
      {outdatedReasons.length > 0 && (
        <LAlert
          type="warning"
          showIcon
          style={{ marginTop: 8 }}
          message="Потенциально устарело"
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {outdatedReasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          }
        />
      )}
      <LSpace wrap style={{ marginTop: 8 }}>
        <LTag color={STATUS_COLORS[job.status]}>{STATUS_LABELS[job.status]}</LTag>
        {gen.provider && <LTag>исполнитель: {gen.provider}</LTag>}
        {gen.backend && gen.backend !== gen.provider && <LTag>бэкенд: {gen.backend}</LTag>}
        {gen.workflow_used && <LTag color="purple">workflow: {gen.workflow_used}</LTag>}
        {gen.plan_id && <LTag color="blue">план: {gen.plan_id}</LTag>}
        {transmitted ? (
          <LTag color="green" title={`sha256: ${gen.input_image_sha256 ?? '—'}`}>
            кадр передан: {gen.reference_image_id}
          </LTag>
        ) : null}
        {gen.input_image_sha256 && (
          <LTag title={gen.input_image_sha256}>sha256: {gen.input_image_sha256.slice(0, 12)}…</LTag>
        )}
        {gen.media_id && <LTag>media: {gen.media_id}</LTag>}
        {gen.size && <LTag>размер: {gen.size}</LTag>}
        {job.fps ? <LTag>{job.fps} fps</LTag> : null}
        {job.duration_sec ? <LTag>{job.duration_sec} с</LTag> : null}
      </LSpace>
    </div>
  );
}

export function VideoPanel({ scene, videoPlan, imageAssetId }: Props) {
  const queryClient = useQueryClient();
  const [executor, setExecutor] = useState<string>('mock');
  const [size, setSize] = useState<string>('1024x576');
  const [jobId, setJobId] = useState<string | null>(null);

  const prompt = videoPlan?.prompt || '';
  const planId = videoPlan?.plan_id || '';
  const cameraMotion = videoPlan?.motion?.camera_motion || '';

  const fullPrompt = useMemo(() => {
    const parts = [prompt.trim()];
    if (cameraMotion) parts.push(`движение камеры: ${cameraMotion}`);
    return parts.filter(Boolean).join('. ');
  }, [prompt, cameraMotion]);

  const imageAssetsQuery = useQuery({
    queryKey: ['studio-image-assets', scene.scene_id],
    queryFn: () => {
      const params = new URLSearchParams({ asset_type: 'image', limit: '30', scene_id: scene.scene_id });
      return api.get(`/book/assets?${params.toString()}`);
    },
    staleTime: 15_000,
  });
  const imageAssets: JobAsset[] = useMemo(
    () => (unwrapData<JobAsset[]>(imageAssetsQuery.data) || []) as JobAsset[],
    [imageAssetsQuery.data],
  );
  const referenceImage = imageAssetId ? imageAssets.find((a) => a.asset_id === imageAssetId) : undefined;

  const jobMutation = useMutation({
    mutationFn: () =>
      api
        .post('/api/studio/video-jobs', {
          chapter: scene.chapter,
          scene_id: scene.scene_id,
          prompt: fullPrompt,
          plan_id: planId || null,
          preferred_backend: executor,
          duration_sec: videoPlan?.duration_sec ?? 8,
          fps: videoPlan?.fps ?? 24,
          size,
          image_asset_id: imageAssetId || null,
        })
        .then(unwrapData<{ asset_id: string; status: string }>),
    onSuccess: (data) => {
      setJobId(data.asset_id);
      toast.success('Видеозадание запущено');
      queryClient.invalidateQueries({ queryKey: ['studio-video-assets', scene.scene_id] });
    },
    onError: (err: Error) => toast.error(`Не удалось запустить задание: ${err.message}`),
  });

  const jobQuery = useQuery({
    queryKey: ['studio-job', jobId],
    queryFn: () => api.get(`/book/assets/${jobId}`).then(unwrapData<JobAsset>),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'completed' || status === 'failed' ? false : 2000;
    },
  });

  const assetsQuery = useQuery({
    queryKey: ['studio-video-assets', scene.scene_id],
    queryFn: () => {
      const params = new URLSearchParams({ asset_type: 'video', limit: '20', scene_id: scene.scene_id });
      return api.get(`/book/assets?${params.toString()}`).then(unwrapData<JobAsset[]>);
    },
    refetchInterval: 5000,
  });
  const assets: JobAsset[] = useMemo(
    () => (unwrapData<JobAsset[]>(assetsQuery.data) || []) as JobAsset[],
    [assetsQuery.data],
  );

  const job = jobQuery.data;
  const jobActive = !!job && (job.status === 'pending' || job.status === 'generating');
  const canRun = !!fullPrompt && !jobMutation.isPending && !jobActive;

  return (
    <div>
      <LCard title="Создание видео" size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <LSelect
            style={{ minWidth: 300 }}
            value={executor}
            onChange={(v) => setExecutor(v as string)}
            options={VIDEO_EXECUTORS}
          />
          <LSelect
            style={{ minWidth: 230 }}
            value={size}
            onChange={(v) => setSize(v as string)}
            options={VIDEO_SIZES}
            aria-label="Размер клипа"
          />
          <LButton
            type="primary"
            icon={<PlayCircleOutlined />}
            disabled={!canRun}
            loading={jobMutation.isPending}
            onClick={() => jobMutation.mutate()}
          >
            Создать видео
          </LButton>
        </div>

        <LSpace wrap style={{ marginTop: 8 }}>
          <span style={{ fontSize: 12, color: '#999' }}>Параметры клипа:</span>
          <LTag style={{ fontSize: 10 }}>
            длительность: {videoPlan?.duration_sec ?? 8} с
          </LTag>
          <LTag style={{ fontSize: 10 }}>{videoPlan?.fps ?? 24} fps</LTag>
          <LTag style={{ fontSize: 10 }}>разрешение: {size}</LTag>
        </LSpace>

        {executor === 'comfyicu' && (
          <div style={{ color: '#b45309', fontSize: 12, marginTop: 8 }}>
            исполнитель списывает кредиты на стороне comfy.icu
          </div>
        )}

        <div style={{ marginTop: 12, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 300px', minWidth: 240 }}>
            <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>Утверждённый кадр (сессии)</div>
            {imageAssetId && referenceImage ? (
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <div style={{ width: 160 }}>
                  <AssetImage asset={referenceImage} approved height={90} />
                </div>
                <div style={{ fontSize: 12 }}>
                  <LTag color="green" style={{ fontSize: 10 }}>утверждён</LTag>
                  <div style={{ color: '#999', marginTop: 4 }}>{referenceImage.asset_id}</div>
                  <div style={{ color: '#999' }}>
                    передаётся исполнителю при запуске — факт передачи виден в статусе задания
                  </div>
                </div>
              </div>
            ) : (
              <LAlert
                type="warning"
                showIcon
                message="Кадр не утверждён"
                description="Видео будет создано без кадра-основы (визуальная связь не гарантирована). Утвердите кадр во вкладке «Изображение»."
              />
            )}
          </div>
          <div style={{ flex: '1 1 300px', minWidth: 240 }}>
            <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>
              Промпт движения (видео)
            </div>
            <textarea
              readOnly
              rows={4}
              value={fullPrompt}
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
            <LSpace wrap style={{ marginTop: 6 }}>
              {videoPlan?.duration_sec ? <LTag style={{ fontSize: 10 }}>{videoPlan.duration_sec} c</LTag> : null}
              {videoPlan?.fps ? <LTag style={{ fontSize: 10 }}>{videoPlan.fps} fps</LTag> : null}
              {planId && <LTag color="blue" style={{ fontSize: 10 }}>{planId}</LTag>}
            </LSpace>
          </div>
        </div>

        {!fullPrompt && (
          <LAlert
            type="info"
            showIcon
            style={{ marginTop: 10 }}
            message="Промпт движения пуст — заполните его во вкладке «Движение»"
          />
        )}
      </LCard>

      <LCard title="Состояние задания" size="small" style={{ marginBottom: 12 }}>
        {jobId ? (
          <div style={{ marginBottom: 8 }}>
            <LTag color="geekblue">задание: {jobId}</LTag>
            <LButton
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => jobQuery.refetch()}
            >
              Обновить статус
            </LButton>
          </div>
        ) : null}
        <JobStatusPanel
          job={job}
          loading={jobQuery.isFetching && !job}
          approvedImageAssetId={imageAssetId}
          referenceImage={referenceImage}
          currentFullPrompt={fullPrompt}
        />
      </LCard>

      <LCard
        title="Видеоартефакты сцены"
        size="small"
        extra={
          <LButton
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => assetsQuery.refetch()}
          />
        }
      >
        {assetsQuery.isLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <LSpin />
          </div>
        ) : assets.length === 0 ? (
          <LEmpty description="Сохранённых видеоартефактов пока нет — запустите первое задание." />
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 12,
            }}
          >
            {assets.map((a) => {
              const staleReasons = videoOutdatedReasons(a, {
                approvedImageAssetId: imageAssetId || null,
                currentFullPrompt: fullPrompt,
              });
              return (
              <LCard key={a.asset_id} size="small" hoverable>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <LBadge status={STATUS_COLORS[a.status]} />
                  <LTag color={STATUS_COLORS[a.status]} style={{ fontSize: 10 }}>
                    {STATUS_LABELS[a.status]}
                  </LTag>
                  <strong style={{ fontSize: 12 }} title={a.title}>
                    {a.title || a.scene_id}
                  </strong>
                </div>
                {a.status === 'completed' && a.file_path ? (
                  <video
                    controls
                    preload="metadata"
                    src={assetFileUrl(a.asset_id)}
                    style={{ width: '100%', borderRadius: 6, background: '#000' }}
                  />
                ) : a.status === 'failed' ? (
                  <LAlert
                    type="error"
                    showIcon
                    message="Ошибка"
                    description={
                      <span style={{ fontFamily: 'monospace', fontSize: 12 }}>
                        {a.error || '—'}
                      </span>
                    }
                  />
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0' }}>
                    <LoadingOutlined /> <span style={{ color: '#999', fontSize: 12 }}>генерация…</span>
                  </div>
                )}
                <LSpace wrap style={{ marginTop: 6 }}>
                  <LTag style={{ fontSize: 10 }}>гл. {a.chapter}</LTag>
                  {a.status === 'completed' && (
                    <LTag color={isMockGeneration(a) ? 'orange' : 'green'} style={{ fontSize: 10 }}>
                      {videoKindLabel(a)}
                    </LTag>
                  )}
                  {staleReasons.length > 0 && (
                    <LTag color="orange" style={{ fontSize: 10 }} title={staleReasons.join('; ')}>
                      потенциально устарело
                    </LTag>
                  )}
                  {a.generation?.reference_image_id ? (
                    <LTag
                      color="green"
                      style={{ fontSize: 10 }}
                      title={`sha256: ${a.generation.input_image_sha256 ?? '—'}`}
                    >
                      передан кадр: {a.generation.reference_image_id}
                    </LTag>
                  ) : (
                    a.status === 'completed' &&
                    imageAssetId && (
                      <LTag color="orange" style={{ fontSize: 10 }}>
                        без кадра-основы (утверждённый не передавался)
                      </LTag>
                    )
                  )}
                  {a.generation?.input_image_sha256 && (
                    <LTag style={{ fontSize: 10 }} title={a.generation.input_image_sha256}>
                      sha256: {a.generation.input_image_sha256.slice(0, 12)}…
                    </LTag>
                  )}
                  {a.generation?.workflow_used && (
                    <LTag color="purple" style={{ fontSize: 10 }}>
                      {a.generation.workflow_used}
                    </LTag>
                  )}
                  {a.generation?.provider && (
                    <LTag style={{ fontSize: 10 }}>{a.generation.provider}</LTag>
                  )}
                </LSpace>
              </LCard>
              );
            })}
          </div>
        )}
      </LCard>
    </div>
  );
}

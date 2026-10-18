'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LButton,
  LCard,
  LEmpty,
  LSpace,
  LSpin,
  LTag,
  toast,
} from '@/shared/ui/light';
import { CheckCircleOutlined, ClockCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { PromptsPanel } from './prompts-panel';
import { ShotsPanel } from './shots-panel';
import { ImagePanel } from './image-panel';
import { VideoPanel } from './video-panel';
import { ArtDirectionPanel } from './art-direction-panel';
import { AffectedPanel } from './affected-panel';
import { ExperimentsPanel } from './experiments-panel';
import { ContinuityPanel } from './continuity-panel';
import { FilmTree } from './film-tree';
import { FilmReel } from './film-reel';
import { FilmSequence } from './sequence';
import { StoryReel } from './story-reel';
import { scenesFromFilm, unwrapData } from './types';
import type {
  ContinuitySummaryT,
  FilmT,
  JobAsset,
  Scene,
  SessionDetailT,
  StudioSessionT,
} from './types';

function StepBadge({
  done,
  active,
  label,
}: {
  done: boolean;
  active?: boolean;
  label: string;
}) {
  return (
    <LTag color={done ? 'success' : active ? 'processing' : 'default'} style={{ fontSize: 11 }}>
      {done ? <CheckCircleOutlined /> : active ? <LoadingOutlined /> : <ClockCircleOutlined />}{' '}
      {label}
    </LTag>
  );
}

function StudioContent() {
  const queryClient = useQueryClient();
  const [sceneKey, setSceneKey] = useState<string | null>(null);

  const scenesQuery = useQuery({
    queryKey: ['studio-film'],
    queryFn: () => api.get('/api/studio/film').then(unwrapData<FilmT>),
    staleTime: 60_000,
  });
  const film = scenesQuery.data || null;
  const scenes = useMemo(() => scenesFromFilm(film), [film]);

  useEffect(() => {
    if (!sceneKey && scenes.length > 0) {
      setSceneKey(`${scenes[0].chapter}:${scenes[0].scene_id}`);
    }
  }, [scenes, sceneKey]);

  const selectedScene = scenes.find((s) => `${s.chapter}:${s.scene_id}` === sceneKey) || null;

  const sessionsQuery = useQuery({
    queryKey: ['studio-sessions'],
    queryFn: () => api.get('/api/studio/list?limit=100').then(unwrapData<StudioSessionT[]>),
  });

  const continuitySummaryQuery = useQuery({
    queryKey: ['studio-continuity-summary'],
    queryFn: () =>
      api.get('/api/studio/continuity/summary').then(unwrapData<ContinuitySummaryT>),
    staleTime: 30_000,
  });
  const continuitySummary = useMemo(() => {
    const data = continuitySummaryQuery.data;
    if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
    return data.scenes || {};
  }, [continuitySummaryQuery.data]);

  const session = useMemo(() => {
    if (!selectedScene) return null;
    return (
      (sessionsQuery.data || []).find(
        (s) => s.chapter === selectedScene.chapter && s.scene_id === selectedScene.scene_id,
      ) || null
    );
  }, [sessionsQuery.data, selectedScene]);

  const detailQuery = useQuery({
    queryKey: ['studio-session', session?.session_id],
    queryFn: () =>
      api.get(`/api/studio/${session!.session_id}`).then(unwrapData<SessionDetailT>),
    enabled: !!session?.session_id,
  });

  const detail = detailQuery.data;
  const liveSession = detail?.session || session;
  const versions = useMemo(() => detail?.versions || [], [detail]);

  const activeVersion = useMemo(() => {
    if (!liveSession || versions.length === 0) return null;
    return (
      versions.find((v) => v.version_id === liveSession.active_version_id) ||
      versions.find((v) => v.is_active) ||
      versions[versions.length - 1] ||
      null
    );
  }, [versions, liveSession]);

  const videoAssetsQuery = useQuery({
    queryKey: ['studio-video-assets', selectedScene?.scene_id],
    queryFn: () => {
      const params = new URLSearchParams({ asset_type: 'video', limit: '20' });
      if (selectedScene) params.set('scene_id', selectedScene.scene_id);
      return api.get(`/book/assets?${params.toString()}`).then(unwrapData<JobAsset[]>);
    },
    enabled: !!selectedScene,
    refetchInterval: 5000,
  });
  const hasVideo = (videoAssetsQuery.data || []).some((a) => a.status === 'completed');

  const createMutation = useMutation({
    mutationFn: (scene: Scene) =>
      api
        .post(`/api/studio/create?chapter=${scene.chapter}&scene_id=${encodeURIComponent(scene.scene_id)}`)
        .then(unwrapData<{ session: StudioSessionT }>),
    onSuccess: () => {
      toast.success('Рабочая область сцены создана');
      queryClient.invalidateQueries({ queryKey: ['studio-sessions'] });
    },
    onError: (err: Error) => toast.error(`Не удалось создать рабочую область: ${err.message}`),
  });

  const sceneLoading = scenesQuery.isLoading;
  const sessionsLoading = sessionsQuery.isLoading;
  const detailLoading = !!session?.session_id && detailQuery.isLoading;

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 4 }}>Studio — рабочая область фильма</h2>
        <span style={{ color: '#999' }}>
          Фильм → эпизоды → сцены → планы · промпт → изображение (утверждение) → видео
        </span>
      </div>

      <LCard
        title="Лента фильма (режиссёрский обзор)"
        size="small"
        style={{ marginBottom: 16 }}
        extra={<LTag color="geekblue">независимо от рабочей области · без монтажа</LTag>}
      >
        <FilmReel
          selectedKey={sceneKey}
          onOpenScene={(s) => setSceneKey(`${s.chapter}:${s.scene_id}`)}
        />
      </LCard>

      <LCard
        title="Последовательность фильма (план сборки)"
        size="small"
        style={{ marginBottom: 16 }}
        extra={<LTag color="geekblue">тайминг · разрывы · переходы · без монтажа</LTag>}
      >
        <FilmSequence />
      </LCard>

      <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <LCard
          title="Фильм · эпизоды и сцены"
          size="small"
          style={{ width: 340, flexShrink: 0 }}
          extra={<LTag color="blue">{film?.film?.scene_count ?? 0} сцен</LTag>}
        >
          <FilmTree film={film} loading={sceneLoading} selectedKey={sceneKey} onSelect={setSceneKey} continuity={continuitySummary} />
        </LCard>

        <div style={{ flex: 1, minWidth: 360 }}>
      <LCard size="small" style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          {!session && selectedScene && (
            <LButton
              type="primary"
              disabled={createMutation.isPending}
              loading={createMutation.isPending}
              onClick={() => createMutation.mutate(selectedScene)}
            >
              Создать рабочую область сцены
            </LButton>
          )}
          {session && (
            <span style={{ fontSize: 12, color: '#999' }}>
              сессия: <strong>{session.session_id}</strong> · статус: {session.status}
            </span>
          )}
        </div>

        {session && liveSession && (
          <LSpace wrap style={{ marginTop: 12 }}>
            <StepBadge done={!!activeVersion} label="1. Промпты" />
            <StepBadge done={!!liveSession.approved_image_asset_id} label="2. Кадр утверждён" />
            <StepBadge done={hasVideo} active={!!liveSession.approved_image_asset_id && !hasVideo} label="3. Видео" />
            <LTag style={{ fontSize: 11 }}>версий: {versions.length}</LTag>
          </LSpace>
        )}
      </LCard>

      {sceneLoading || sessionsLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <LSpin />
        </div>
      ) : !selectedScene ? (
        <LEmpty description="Выберите сцену книги, чтобы открыть рабочую область." />
      ) : !session ? (
        <LEmpty
          description={`Для сцены «${selectedScene.title || selectedScene.scene_id}» ещё нет рабочей области. Нажмите «Создать рабочую область сцены» — будут собраны промпты трёх слоёв (контент, изображение, движение).`}
        />
      ) : detailLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <LSpin />
        </div>
      ) : !detail || !activeVersion || !liveSession ? (
        <LEmpty description="Не удалось загрузить версии рабочей области." />
      ) : (
        <div>
          <LCard
            title="0 · Правила фильма (арт-дирекшн)"
            size="small"
            style={{ marginBottom: 12 }}
            extra={<LTag>единый визуальный язык</LTag>}
          >
            <ArtDirectionPanel session={liveSession} />
          </LCard>

          <LCard
            title="0.1 · Затронутые кадры (управляемое обновление)"
            size="small"
            style={{ marginBottom: 12 }}
            extra={<LTag color="orange">подготовка · генерация · утверждение</LTag>}
          >
            <AffectedPanel session={liveSession} />
          </LCard>

          <LCard
            title="0.2 · История экспериментов"
            size="small"
            style={{ marginBottom: 12 }}
            extra={<LTag color="blue">группировка · пагинация · очистка</LTag>}
          >
            <ExperimentsPanel session={liveSession} />
          </LCard>

          <LCard
            title="1 · Промпты сцены"
            size="small"
            style={{ marginBottom: 12 }}
            extra={<LTag color="blue">v{activeVersion.version_number}</LTag>}
          >
            <PromptsPanel
              session={liveSession}
              versions={versions}
              activeVersion={activeVersion}
              references={detail.references}
            />
          </LCard>

          <LCard
            title="Планы сцены (шоты)"
            size="small"
            style={{ marginBottom: 12 }}
            extra={<LTag>содержание · раздельное поле</LTag>}
          >
            <ShotsPanel session={liveSession} activeVersion={activeVersion} />
          </LCard>

          <LCard
            title="1.1 · Связность и согласование"
            size="small"
            style={{ marginBottom: 12 }}
            extra={<LTag color="purple">планы · сцены · эпизоды</LTag>}
          >
            <ContinuityPanel session={liveSession} />
          </LCard>

          <LCard title="2 · Изображение" size="small" style={{ marginBottom: 12 }}>
            <ImagePanel
              scene={selectedScene}
              session={liveSession}
              imagePlan={activeVersion.image_description}
            />
          </LCard>

          <LCard title="3 · Видео" size="small" style={{ marginBottom: 12 }}>
            <VideoPanel
              scene={selectedScene}
              videoPlan={activeVersion.video_description}
              imageAssetId={liveSession.approved_image_asset_id}
            />
          </LCard>

          <LCard
            title="4 · Лента сцены"
            size="small"
            style={{ marginBottom: 12 }}
            extra={<LTag color="geekblue">эпизод · сцена · план · кадр · клип</LTag>}
          >
            <StoryReel scene={selectedScene} />
          </LCard>
        </div>
      )}
        </div>
      </div>
    </div>
  );
}

export default function StudioPage() {
  return (
    <ProtectedRoute>
      <StudioContent />
    </ProtectedRoute>
  );
}

'use client';

/**
 * Лента сцены (Story Reel, Фаза 3): режиссёрский просмотр «Эпизод → Сцена →
 * План → Кадр → Клип».
 *
 * Read-only проекция: порядок берётся из канонических данных (геном → сцены,
 * сценарий → планы), ассеты только привязываются. Лента НЕ монтирует фильм,
 * не создаёт MP4 и не запускает платную генерацию. Кнопка «Создать видео из
 * утверждённого кадра» использует существующий механизм видео-заданий
 * (по умолчанию mock — без трат).
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LAlert, LButton, LCard, LEmpty, LSelect, LSpace, LSpin, LTag, toast } from '@/shared/ui/light';
import {
  CaretRightOutlined,
  LeftOutlined,
  PauseOutlined,
  ReloadOutlined,
  RightOutlined,
} from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import {
  CONTINUITY_RELATION_LABELS,
  CONTINUITY_STATUS_COLORS,
  CONTINUITY_STATUS_LABELS,
  REEL_CLIP_COLORS,
  REEL_CLIP_LABELS,
  REEL_FRAME_COLORS,
  REEL_FRAME_LABELS,
  REEL_KIND_LABELS,
  assetFileUrl,
  unwrapData,
} from './types';
import type {
  ReelLinkT,
  ReelScope,
  ReelSceneT,
  ReelSequenceItemT,
  ReelShotT,
  ReelT,
  Scene,
} from './types';

type Props = {
  scene: Scene;
};

const SCOPES: { value: ReelScope; label: string }[] = [
  { value: 'scene', label: 'Эта сцена' },
  { value: 'sequence', label: 'Последовательность' },
  { value: 'episode', label: 'Весь эпизод' },
];

export function fmtDuration(sec: number): string {
  const s = Math.max(0, Math.round(sec || 0));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return m > 0 ? `${m}:${String(r).padStart(2, '0')}` : `${r} с`;
}

const EMPTY_SUMMARY = {
  scene_count: 0,
  shot_count: 0,
  clip_count: 0,
  frame_count: 0,
  placeholder_count: 0,
  mock_count: 0,
  stale_count: 0,
  total_duration_sec: 0,
};

/** Защита от неполных/чужих ответов: без сцен считаем ленту пустой. */
export function normalizeReel(raw: unknown): ReelT | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Partial<ReelT>;
  if (!Array.isArray(r.scenes) || r.scenes.length === 0) return null;
  return {
    scope: r.scope ?? 'scene',
    chapter: r.chapter ?? 0,
    scene_ids: Array.isArray(r.scene_ids) ? r.scene_ids : [],
    film: r.film ?? { book_id: '', title: '' },
    scenes: r.scenes,
    sequence: Array.isArray(r.sequence) ? r.sequence : [],
    summary: { ...EMPTY_SUMMARY, ...(r.summary ?? {}) },
    limitations: Array.isArray(r.limitations) ? r.limitations : [],
  };
}

export function ContinuityInline({ link }: { link: ReelLinkT | null }) {
  if (!link) return null;
  const status = link.status;
  return (
    <span
      data-testid="reel-continuity"
      title={link.findings.map((f) => f.message).join('\n')}
      style={{ fontSize: 11, color: '#666' }}
    >
      <LTag color={CONTINUITY_STATUS_COLORS[status] || 'default'} style={{ fontSize: 10 }}>
        {CONTINUITY_STATUS_LABELS[status] || status}
      </LTag>
      {link.finding_count > 0 && <span> отличий: {link.finding_count}</span>}
    </span>
  );
}

function ShotCard({
  scene,
  shot,
  onCreateVideo,
  busy,
}: {
  scene: ReelSceneT;
  shot: ReelShotT;
  onCreateVideo: (scene: ReelSceneT, shot: ReelShotT) => void;
  busy: boolean;
}) {
  const clip = shot.video;
  const hasClip = clip.status === 'ready' || clip.status === 'mock' || clip.status === 'stale';
  const canCreate = shot.frame.status === 'approved' && !!shot.frame.asset_id && busy === false;
  return (
    <div
      data-testid="reel-shot"
      style={{
        border: '1px solid var(--card-border, #eee)',
        borderRadius: 8,
        padding: 10,
        marginBottom: 8,
        display: 'flex',
        gap: 12,
        flexWrap: 'wrap',
      }}
    >
      <div style={{ width: 160, flexShrink: 0 }}>
        {hasClip && clip.asset_id ? (
          <video
            controls
            preload="metadata"
            src={assetFileUrl(clip.asset_id)}
            style={{ width: '100%', borderRadius: 6, background: '#000' }}
          />
        ) : shot.frame.asset_id ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            alt={shot.description || shot.shot_id}
            src={assetFileUrl(shot.frame.asset_id)}
            style={{ width: '100%', borderRadius: 6, background: '#000' }}
          />
        ) : (
          <div
            style={{
              height: 90,
              borderRadius: 6,
              background: 'rgba(127,127,127,0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#999',
              fontSize: 12,
            }}
          >
            нет материала
          </div>
        )}
      </div>

      <div style={{ flex: 1, minWidth: 240 }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
          <strong style={{ fontSize: 13 }}>
            План {shot.index + 1} · {shot.shot_type || '—'}
          </strong>
          <LTag style={{ fontSize: 10 }}>{shot.duration_sec} с</LTag>
          {shot.transition_to_next ? (
            <LTag style={{ fontSize: 10 }} color="blue">
              переход: {shot.transition_to_next}
            </LTag>
          ) : null}
        </div>

        {shot.description ? (
          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{shot.description}</div>
        ) : null}

        <LSpace wrap style={{ marginTop: 6 }}>
          <LTag color={REEL_FRAME_COLORS[shot.frame.status]} style={{ fontSize: 10 }}>
            {REEL_FRAME_LABELS[shot.frame.status]}
          </LTag>
          <LTag color={REEL_CLIP_COLORS[clip.status]} style={{ fontSize: 10 }}>
            {REEL_CLIP_LABELS[clip.status]}
          </LTag>
          {clip.executor?.provider || clip.executor?.backend ? (
            <LTag style={{ fontSize: 10 }}>исполнитель: {clip.executor.provider || clip.executor.backend}</LTag>
          ) : null}
        </LSpace>

        {clip.stale_reasons.length > 0 && (
          <div style={{ fontSize: 11, color: '#b45309', marginTop: 4 }}>
            {clip.stale_reasons.join('; ')}
          </div>
        )}

        <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <ContinuityInline link={shot.continuity_next} />
          <span style={{ flex: 1 }} />
          {!hasClip && canCreate && (
            <LButton
              size="small"
              type="primary"
              disabled={busy}
              onClick={() => onCreateVideo(scene, shot)}
            >
              Создать видео из утверждённого кадра
            </LButton>
          )}
          {!hasClip && !canCreate && shot.frame.status !== 'approved' && (
            <span style={{ fontSize: 11, color: '#999' }}>нужен утверждённый кадр</span>
          )}
        </div>
      </div>
    </div>
  );
}

function SceneReel({
  scene,
  onCreateVideo,
  busy,
}: {
  scene: ReelSceneT;
  onCreateVideo: (scene: ReelSceneT, shot: ReelShotT) => void;
  busy: boolean;
}) {
  return (
    <div data-testid="reel-scene" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 13 }}>
          Эпизод {scene.chapter} · Сцена {scene.index_in_episode + 1} · {scene.title || scene.scene_id}
        </strong>
        {scene.location && <LTag style={{ fontSize: 10 }}>{scene.location}</LTag>}
        <LTag style={{ fontSize: 10 }}>{scene.shot_count} планов</LTag>
        <LTag style={{ fontSize: 10 }}>{fmtDuration(scene.total_duration_sec)}</LTag>
        {scene.transfer?.applied && (
          <LTag color="processing" style={{ fontSize: 10 }}>
            учитывается перенос из: Сцена {scene.transfer.from_scene_id}
          </LTag>
        )}
        {scene.transfer?.stale && !scene.transfer.applied && (
          <LTag color="warning" style={{ fontSize: 10 }}>
            перенос устарел — требуется подтверждение
          </LTag>
        )}
      </div>

      {scene.continuity_from_prev_scene && (
        <div style={{ marginTop: 4 }}>
          <span style={{ fontSize: 11, color: '#999' }}>
            {CONTINUITY_RELATION_LABELS[scene.continuity_from_prev_scene.relation] || 'Граница сцен'}:{' '}
          </span>
          <ContinuityInline link={scene.continuity_from_prev_scene} />
        </div>
      )}

      <div style={{ marginTop: 8 }}>
        {scene.shots.length === 0 ? (
          <LEmpty description="У сцены нет активного сценарного плана — планы не отображаются." />
        ) : (
          scene.shots.map((shot) => (
            <ShotCard key={shot.shot_id} scene={scene} shot={shot} onCreateVideo={onCreateVideo} busy={busy} />
          ))
        )}
      </div>
    </div>
  );
}

/** Последовательный предпросмотр: клип → видео, кадр → изображение. Без ffmpeg. */
export function ReelPlayer({ sequence }: { sequence: ReelSequenceItemT[] }) {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setIndex(0);
    setPlaying(false);
  }, [sequence]);

  const item: ReelSequenceItemT | undefined = sequence[index];

  useEffect(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (!playing || !item) return;
    if (item.kind === 'clip') return; // клип контролируется <video>
    const ms = Math.max(500, (item.duration_sec || 1) * 1000);
    timer.current = setTimeout(() => {
      setIndex((i) => (i + 1 < sequence.length ? i + 1 : i));
    }, ms);
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [playing, item, sequence.length]);

  if (sequence.length === 0) {
    return <LEmpty description="В выбранной области нет планов для предпросмотра." />;
  }

  const total = sequence.reduce((acc, s) => acc + (s.duration_sec || 0), 0);

  return (
    <div data-testid="reel-player">
      <div
        style={{
          background: '#000',
          borderRadius: 8,
          minHeight: 220,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {item?.kind === 'clip' && item.clip_asset_id ? (
          <video
            key={item.clip_asset_id}
            autoPlay={playing}
            controls
            src={assetFileUrl(item.clip_asset_id)}
            style={{ maxWidth: '100%', maxHeight: 380 }}
          />
        ) : item?.kind === 'frame' && item.frame_asset_id ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            alt={item.description || item.shot_id}
            src={assetFileUrl(item.frame_asset_id)}
            style={{ maxWidth: '100%', maxHeight: 380 }}
          />
        ) : (
          <span style={{ color: '#888', fontSize: 13 }}>нет материала — план пропущен</span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
        <LButton
          size="small"
          icon={playing ? <PauseOutlined /> : <CaretRightOutlined />}
          onClick={() => setPlaying((p) => !p)}
        >
          {playing ? 'Пауза' : 'Воспроизвести'}
        </LButton>
        <LButton
          size="small"
          icon={<LeftOutlined />}
          disabled={index === 0}
          onClick={() => setIndex((i) => Math.max(0, i - 1))}
        />
        <LButton
          size="small"
          icon={<RightOutlined />}
          disabled={index >= sequence.length - 1}
          onClick={() => setIndex((i) => Math.min(sequence.length - 1, i + 1))}
        />
        <LTag style={{ fontSize: 11 }}>
          {index + 1} / {sequence.length}
        </LTag>
        <LTag style={{ fontSize: 11 }}>{REEL_KIND_LABELS[item?.kind || 'placeholder']}</LTag>
        <span style={{ fontSize: 12, color: '#999' }}>
          Эпизод {item?.chapter} · Сцена {(item?.index_in_episode ?? 0) + 1} · План{' '}
          {(item?.shot_index ?? 0) + 1} · всего {fmtDuration(total)}
        </span>
      </div>
    </div>
  );
}

export function StoryReel({ scene }: Props) {
  const queryClient = useQueryClient();
  const [scope, setScope] = useState<ReelScope>('scene');
  const [fromScene, setFromScene] = useState<string>(scene.scene_id);
  const [toScene, setToScene] = useState<string>(scene.scene_id);

  useEffect(() => {
    setFromScene(scene.scene_id);
    setToScene(scene.scene_id);
  }, [scene.scene_id]);

  const scenesQuery = useQuery({
    queryKey: ['studio-scenes'],
    queryFn: () =>
      api.get('/api/studio/scenes').then(unwrapData<{ scene_id: string; chapter: number; title: string }[]>),
    staleTime: 60_000,
  });
  const chapterScenes = useMemo(
    () => (scenesQuery.data || []).filter((s) => s.chapter === scene.chapter),
    [scenesQuery.data, scene.chapter],
  );
  const sceneOptions = useMemo(
    () =>
      chapterScenes.map((s, i) => ({
        value: s.scene_id,
        label: `Сцена ${i + 1} · ${s.title || s.scene_id}`,
      })),
    [chapterScenes],
  );

  const sequenceIds = useMemo(() => {
    if (scope !== 'sequence') return [];
    const ids = chapterScenes.map((s) => s.scene_id);
    const a = ids.indexOf(fromScene);
    const b = ids.indexOf(toScene);
    if (a < 0 || b < 0) return [];
    const [lo, hi] = a <= b ? [a, b] : [b, a];
    return ids.slice(lo, hi + 1);
  }, [scope, chapterScenes, fromScene, toScene]);

  const reelQuery = useQuery({
    queryKey: ['studio-reel', scope, scene.chapter, scene.scene_id, scope === 'sequence' ? sequenceIds.join(',') : ''],
    queryFn: () => {
      const params = new URLSearchParams({ chapter: String(scene.chapter) });
      if (scope === 'scene') params.set('scene_id', scene.scene_id);
      else if (scope === 'sequence') params.set('scene_ids', sequenceIds.join(','));
      return api.get(`/api/studio/reel?${params.toString()}`).then(unwrapData<ReelT>);
    },
    enabled: scope !== 'sequence' || sequenceIds.length > 0,
  });

  const reel = useMemo(() => normalizeReel(reelQuery.data), [reelQuery.data]);

  const createVideo = useMutation({
    mutationFn: ({ scene: sc, shot }: { scene: ReelSceneT; shot: ReelShotT }) =>
      api
        .post('/api/studio/video-jobs', {
          chapter: sc.chapter,
          scene_id: sc.scene_id,
          prompt: shot.resolved_prompt,
          plan_id: null,
          shot_id: shot.shot_id,
          preferred_backend: 'mock',
          image_asset_id: shot.frame.asset_id,
          title: `Видео плана ${shot.shot_id}`,
        })
        .then(unwrapData<{ asset_id: string; status: string }>),
    onSuccess: () => {
      toast.success('Видеозадание создано (mock). Обновите ленту после завершения.');
      queryClient.invalidateQueries({ queryKey: ['studio-reel'] });
      queryClient.invalidateQueries({ queryKey: ['studio-video-assets'] });
    },
    onError: (err: Error) => toast.error(`Не удалось создать видео: ${err.message}`),
  });

  const busy = createVideo.isPending;

  return (
    <div data-testid="story-reel">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ fontSize: 13, color: '#666' }}>Область просмотра:</span>
        {SCOPES.map((s) => (
          <LButton
            key={s.value}
            size="small"
            type={scope === s.value ? 'primary' : 'default'}
            onClick={() => setScope(s.value)}
          >
            {s.label}
          </LButton>
        ))}
        <span style={{ flex: 1 }} />
        <LButton
          size="small"
          icon={<ReloadOutlined />}
          onClick={() => reelQuery.refetch()}
          loading={reelQuery.isFetching}
        >
          Обновить
        </LButton>
      </div>

      {scope === 'sequence' && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
          <LSelect
            style={{ minWidth: 220 }}
            value={fromScene}
            onChange={(v) => setFromScene(v as string)}
            options={sceneOptions}
            aria-label="С первой сцены"
          />
          <LSelect
            style={{ minWidth: 220 }}
            value={toScene}
            onChange={(v) => setToScene(v as string)}
            options={sceneOptions}
            aria-label="По сцену"
          />
          <span style={{ fontSize: 12, color: '#999', alignSelf: 'center' }}>
            Порядок канонический — лента не переупорядочивает сцены.
          </span>
        </div>
      )}

      {reelQuery.isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <LSpin />
        </div>
      ) : reelQuery.isError ? (
        <LEmpty description="Не удалось загрузить ленту фильма." />
      ) : !reel || reel.scenes.length === 0 ? (
        <LEmpty description="В выбранной области нет сцен." />
      ) : (
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              flexWrap: 'wrap',
              marginBottom: 8,
            }}
          >
            <LTag color="geekblue" style={{ fontSize: 11 }}>
              сцен: {reel.summary.scene_count}
            </LTag>
            <LTag style={{ fontSize: 11 }}>планов: {reel.summary.shot_count}</LTag>
            <LTag color="green" style={{ fontSize: 11 }}>
              клипов: {reel.summary.clip_count}
            </LTag>
            <LTag color="blue" style={{ fontSize: 11 }}>
              кадров: {reel.summary.frame_count}
            </LTag>
            <LTag style={{ fontSize: 11 }}>без материала: {reel.summary.placeholder_count}</LTag>
            {reel.summary.mock_count > 0 && (
              <LTag color="orange" style={{ fontSize: 11 }}>
                mock: {reel.summary.mock_count}
              </LTag>
            )}
            {reel.summary.stale_count > 0 && (
              <LTag color="warning" style={{ fontSize: 11 }}>
                устарело: {reel.summary.stale_count}
              </LTag>
            )}
            <LTag style={{ fontSize: 11 }}>длительность: {fmtDuration(reel.summary.total_duration_sec)}</LTag>
          </div>

          <LCard title="Предпросмотр области" size="small" style={{ marginBottom: 12 }}>
            <ReelPlayer sequence={reel.sequence} />
          </LCard>

          {reel.scenes.map((sc) => (
            <SceneReel
              key={sc.scene_id}
              scene={sc}
              busy={busy}
              onCreateVideo={(sceneT, shot) => createVideo.mutate({ scene: sceneT, shot })}
            />
          ))}

          {reel.limitations.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {reel.limitations.map((l, i) => (
                <div key={i} style={{ fontSize: 12, color: '#999' }}>
                  {l}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <LAlert
        type="info"
        showIcon
        style={{ marginTop: 12 }}
        message="Это режиссёрский просмотр, а не монтаж."
        description="Лента показывает порядок и материалы, но не собирает финальный фильм (без MP4). «Создать видео из утверждённого кадра» использует существующий механизм видео-заданий (по умолчанию mock — без трат)."
      />
    </div>
  );
}

'use client';

/**
 * Лента фильма (Film Reel): режиссёрский обзор всего фильма «Эпизод → Сцена →
 * План → Кадр → Клип», независимый от выбранной Studio-сессии.
 *
 * Это навигационный/режиссёрский слой представления состояния, а НЕ монтаж:
 * порядок берётся из канонических данных (геном → сцены, сценарий → планы),
 * материалы только показываются. Кнопка «Открыть в Studio» переводит к рабочей
 * области сцены, где и происходит утверждение кадров и создание клипов.
 *
 * Фильтр/поиск работает на клиенте: данные всего фильма уже загружены целиком,
 * новый API и новые сущности не создаются. Фильтр только сужает показ и НЕ
 * меняет порядок канонических сцен/планов.
 */

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { LButton, LCard, LEmpty, LInput, LSpace, LSpin, LTag } from '@/shared/ui/light';
import { ReloadOutlined, RightOutlined, SearchOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import {
  REEL_CLIP_COLORS,
  REEL_CLIP_LABELS,
  REEL_FRAME_COLORS,
  REEL_FRAME_LABELS,
  REEL_KIND_LABELS,
  unwrapData,
} from './types';
import type { ReelSceneT, ReelT, ReelSequenceItemT, ReelShotT } from './types';
import { ContinuityInline, ReelPlayer, fmtDuration, normalizeReel } from './story-reel';

type Props = {
  onOpenScene: (scene: { scene_id: string; chapter: number }) => void;
  selectedKey?: string | null;
};

type ReelStatus =
  | 'all'
  | 'clip'
  | 'mock'
  | 'stale'
  | 'frame_no_clip'
  | 'needs_update'
  | 'placeholder'
  | 'no_session'
  | 'continuity';

const STATUS_FILTERS: { value: ReelStatus; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'clip', label: 'Есть клип' },
  { value: 'mock', label: 'Mock' },
  { value: 'stale', label: 'Устарело' },
  { value: 'frame_no_clip', label: 'Кадр без клипа' },
  { value: 'needs_update', label: 'Требует обновления' },
  { value: 'placeholder', label: 'Нет материала' },
  { value: 'no_session', label: 'Без рабочей области' },
  { value: 'continuity', label: 'Несоответствие' },
];

function isClipStatus(status: string): boolean {
  return status === 'ready' || status === 'mock' || status === 'stale';
}

function isFrameReady(status: string): boolean {
  return status === 'approved' || status === 'needs_update';
}

/** Сценарный уровень фильтра (не по отдельному плану). */
function isSceneLevelStatus(status: ReelStatus): boolean {
  return status === 'no_session' || status === 'continuity';
}

function shotMatchesStatus(shot: ReelShotT, status: ReelStatus): boolean {
  const clip = shot.video.status;
  switch (status) {
    case 'clip':
      return isClipStatus(clip);
    case 'mock':
      return clip === 'mock';
    case 'stale':
      return clip === 'stale';
    case 'frame_no_clip':
      return isFrameReady(shot.frame.status) && !isClipStatus(clip);
    case 'needs_update':
      return shot.frame.status === 'needs_update';
    case 'placeholder':
      return !isClipStatus(clip) && !isFrameReady(shot.frame.status);
    default:
      return true;
  }
}

function sceneMatchesStatus(scene: ReelSceneT, status: ReelStatus): boolean {
  switch (status) {
    case 'no_session':
      return !scene.has_session;
    case 'continuity':
      return (
        scene.continuity_from_prev_scene?.status === 'mismatch' ||
        scene.shots.some((sh) => sh.continuity_next?.status === 'mismatch')
      );
    default:
      return true;
  }
}

function textMatches(query: string, values: (string | undefined | null)[]): boolean {
  return values.some((v) => (v || '').toLowerCase().includes(query));
}

function sceneTextMatch(scene: ReelSceneT, query: string): boolean {
  return textMatches(query, [
    scene.title,
    scene.scene_id,
    scene.location,
    ...(scene.characters || []),
  ]);
}

function shotTextMatch(shot: ReelShotT, query: string): boolean {
  return textMatches(query, [shot.description, shot.shot_type, shot.shot_id]);
}

function sceneCounts(scene: ReelSceneT) {
  let clips = 0;
  let frames = 0;
  let stale = 0;
  for (const sh of scene.shots) {
    if (isClipStatus(sh.video.status)) {
      clips += 1;
      if (sh.video.status === 'stale') stale += 1;
    } else if (isFrameReady(sh.frame.status)) {
      frames += 1;
    }
  }
  return { clips, frames, stale };
}

/**
 * Применить фильтр к ленте, НЕ меняя порядок сцен и планов.
 * Всегда возвращает копии сцен (с урезанным при необходимости списком планов).
 */
function filterReel(
  scenes: ReelSceneT[],
  { episode, query, status }: { episode: number | 'all'; query: string; status: ReelStatus },
): ReelSceneT[] {
  const q = query.trim().toLowerCase();
  const shotLevel = status !== 'all' && !isSceneLevelStatus(status);

  const result: ReelSceneT[] = [];
  for (const scene of scenes) {
    if (episode !== 'all' && scene.chapter !== episode) continue;
    const sceneText = q ? sceneTextMatch(scene, q) : false;

    if (isSceneLevelStatus(status)) {
      if (!sceneMatchesStatus(scene, status)) continue;
      const shots = q ? scene.shots.filter((sh) => sceneText || shotTextMatch(sh, q)) : scene.shots;
      if (q && shots.length === 0) continue;
      result.push({ ...scene, shots });
      continue;
    }

    if (!q && !shotLevel) {
      result.push(scene);
      continue;
    }

    const shots = scene.shots.filter((sh) => {
      const textOk = !q || sceneText || shotTextMatch(sh, q);
      const statusOk = !shotLevel || shotMatchesStatus(sh, status);
      return textOk && statusOk;
    });
    if (shots.length === 0) continue;
    result.push({ ...scene, shots });
  }
  return result;
}

function ShotRow({ shot }: { shot: ReelShotT }) {
  const clip = shot.video;
  return (
    <div
      data-testid="film-reel-shot"
      style={{
        display: 'flex',
        gap: 8,
        alignItems: 'center',
        flexWrap: 'wrap',
        padding: '3px 0',
        fontSize: 12,
        borderTop: '1px dashed rgba(127,127,127,0.2)',
      }}
    >
      <span style={{ minWidth: 66, color: '#888' }}>План {shot.index + 1}</span>
      <span style={{ color: '#999', minWidth: 90 }}>{shot.shot_type || '—'}</span>
      <LTag color="purple" style={{ fontSize: 10 }}>
        {REEL_KIND_LABELS[isClipStatus(clip.status) ? 'clip' : shot.frame.asset_id ? 'frame' : 'placeholder']}
      </LTag>
      <LTag color={REEL_FRAME_COLORS[shot.frame.status]} style={{ fontSize: 10 }}>
        {REEL_FRAME_LABELS[shot.frame.status]}
      </LTag>
      <LTag color={REEL_CLIP_COLORS[clip.status]} style={{ fontSize: 10 }}>
        {REEL_CLIP_LABELS[clip.status]}
      </LTag>
      <LTag style={{ fontSize: 10 }}>{shot.duration_sec} с</LTag>
      <ContinuityInline link={shot.continuity_next} />
      {clip.stale_reasons.length > 0 && (
        <span style={{ fontSize: 11, color: '#b45309' }}>{clip.stale_reasons.join('; ')}</span>
      )}
    </div>
  );
}

function SceneRow({
  scene,
  selectedKey,
  onOpenScene,
}: {
  scene: ReelSceneT;
  selectedKey?: string | null;
  onOpenScene: Props['onOpenScene'];
}) {
  const counts = sceneCounts(scene);
  const key = `${scene.chapter}:${scene.scene_id}`;
  const selected = selectedKey === key;
  return (
    <div
      data-testid="film-reel-scene"
      style={{
        border: selected ? '1px solid #1677ff' : '1px solid var(--card-border, #eee)',
        borderRadius: 8,
        padding: 8,
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 12 }}>
          Сцена {scene.index_in_episode + 1} · {scene.title || scene.scene_id}
        </strong>
        {scene.location && <LTag style={{ fontSize: 10 }}>{scene.location}</LTag>}
        <LTag style={{ fontSize: 10 }}>{scene.shot_count} планов</LTag>
        <LTag style={{ fontSize: 10 }}>{fmtDuration(scene.total_duration_sec)}</LTag>
        {counts.frames > 0 && (
          <LTag color="blue" style={{ fontSize: 10 }}>
            кадров: {counts.frames}
          </LTag>
        )}
        {counts.clips > 0 && (
          <LTag color="green" style={{ fontSize: 10 }}>
            клипов: {counts.clips}
          </LTag>
        )}
        {counts.stale > 0 && (
          <LTag color="warning" style={{ fontSize: 10 }}>
            устарело: {counts.stale}
          </LTag>
        )}
        {!scene.has_session && (
          <LTag style={{ fontSize: 10 }} color="default">
            нет рабочей области
          </LTag>
        )}
        {scene.transfer?.applied && (
          <LTag color="processing" style={{ fontSize: 10 }}>
            перенос из: {scene.transfer.from_scene_id}
          </LTag>
        )}
        {scene.transfer?.stale && !scene.transfer.applied && (
          <LTag color="warning" style={{ fontSize: 10 }}>
            перенос устарел
          </LTag>
        )}
        <span style={{ flex: 1 }} />
        <LButton
          size="small"
          icon={<RightOutlined />}
          onClick={() => onOpenScene({ scene_id: scene.scene_id, chapter: scene.chapter })}
        >
          Открыть в Studio
        </LButton>
      </div>

      {scene.continuity_from_prev_scene && (
        <div style={{ marginTop: 4 }}>
          <ContinuityInline link={scene.continuity_from_prev_scene} />
        </div>
      )}

      {scene.shots.length > 0 && (
        <div style={{ marginTop: 6 }}>
          {scene.shots.map((shot) => (
            <ShotRow key={shot.shot_id} shot={shot} />
          ))}
        </div>
      )}
    </div>
  );
}

function FilterChips<T extends string | number>({
  options,
  value,
  onChange,
  testidPrefix,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  testidPrefix: string;
}) {
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
      {options.map((o) => (
        <span key={String(o.value)} data-testid={`${testidPrefix}-${o.value}`}>
          <LButton
            size="small"
            type={value === o.value ? 'primary' : 'default'}
            onClick={() => onChange(o.value)}
          >
            {o.label}
          </LButton>
        </span>
      ))}
    </div>
  );
}

export function FilmReel({ onOpenScene, selectedKey }: Props) {
  const [episode, setEpisode] = useState<number | 'all'>('all');
  const [status, setStatus] = useState<ReelStatus>('all');
  const [query, setQuery] = useState('');

  const reelQuery = useQuery({
    queryKey: ['studio-film-reel'],
    queryFn: () => api.get('/api/studio/reel').then(unwrapData<ReelT>),
    staleTime: 15_000,
  });

  const reel = useMemo(() => normalizeReel(reelQuery.data), [reelQuery.data]);

  const episodeOptions = useMemo(() => {
    if (!reel) return [] as { value: number | 'all'; label: string }[];
    const chapters = Array.from(new Set(reel.scenes.map((s) => s.chapter)));
    return [
      { value: 'all' as const, label: 'Все эпизоды' },
      ...chapters.map((ch) => ({ value: ch, label: `Эпизод ${ch}` })),
    ];
  }, [reel]);

  const filteredScenes = useMemo(
    () => (reel ? filterReel(reel.scenes, { episode, query, status }) : []),
    [reel, episode, query, status],
  );

  const isFiltering = episode !== 'all' || status !== 'all' || query.trim() !== '';

  const filteredSummary = useMemo(() => {
    let clips = 0;
    let frames = 0;
    let placeholders = 0;
    let mock = 0;
    let stale = 0;
    let shots = 0;
    let duration = 0;
    for (const sc of filteredScenes) {
      for (const sh of sc.shots) {
        shots += 1;
        duration += sh.duration_sec || 0;
        if (isClipStatus(sh.video.status)) {
          clips += 1;
          if (sh.video.status === 'mock') mock += 1;
          if (sh.video.status === 'stale') stale += 1;
        } else if (isFrameReady(sh.frame.status)) {
          frames += 1;
        } else {
          placeholders += 1;
        }
      }
    }
    return {
      scene_count: filteredScenes.length,
      shot_count: shots,
      clip_count: clips,
      frame_count: frames,
      placeholder_count: placeholders,
      mock_count: mock,
      stale_count: stale,
      total_duration_sec: Math.round(duration * 100) / 100,
    };
  }, [filteredScenes]);

  const filteredSequence = useMemo<ReelSequenceItemT[]>(() => {
    if (!reel) return [];
    if (!isFiltering) return reel.sequence;
    const keys = new Set<string>();
    for (const sc of filteredScenes) {
      for (const sh of sc.shots) keys.add(`${sc.scene_id}\u0000${sh.shot_id}`);
    }
    return reel.sequence.filter((it) => keys.has(`${it.scene_id}\u0000${it.shot_id}`));
  }, [reel, isFiltering, filteredScenes]);

  const episodes = useMemo(() => {
    const groups: { chapter: number; scenes: ReelSceneT[] }[] = [];
    for (const sc of filteredScenes) {
      const last = groups[groups.length - 1];
      if (last && last.chapter === sc.chapter) last.scenes.push(sc);
      else groups.push({ chapter: sc.chapter, scenes: [sc] });
    }
    return groups;
  }, [filteredScenes]);

  return (
    <div data-testid="film-reel">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ fontSize: 13, color: '#666' }}>
          Весь фильм — режиссёрский обзор состояния сцен, планов, кадров и клипов.
        </span>
        <span style={{ flex: 1 }} />
        <LButton
          size="small"
          icon={<ReloadOutlined />}
          loading={reelQuery.isFetching}
          onClick={() => reelQuery.refetch()}
        >
          Обновить
        </LButton>
      </div>

      {reelQuery.isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <LSpin />
        </div>
      ) : reelQuery.isError ? (
        <LEmpty description="Не удалось загрузить ленту фильма." />
      ) : !reel ? (
        <LEmpty description="Сцены книги не найдены." />
      ) : (
        <div>
          <div style={{ marginBottom: 8 }}>
            <LInput
              size="small"
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Поиск: сцена, локация, персонаж, описание плана…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ width: 360 }}
            />
          </div>

          <div style={{ marginBottom: 6 }}>
            <span style={{ fontSize: 11, color: '#999', marginRight: 6 }}>Эпизод:</span>
            <FilterChips
              testidPrefix="film-reel-episode-filter"
              options={episodeOptions}
              value={episode}
              onChange={setEpisode}
            />
          </div>

          <div style={{ marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: '#999', marginRight: 6 }}>Показать только:</span>
            <FilterChips
              testidPrefix="film-reel-status-filter"
              options={STATUS_FILTERS}
              value={status}
              onChange={(v) => setStatus(v as ReelStatus)}
            />
          </div>

          <LSpace wrap style={{ marginBottom: 8 }}>
            <LTag color="geekblue" style={{ fontSize: 11 }}>
              эпизодов: {reel.film.episode_count ?? episodeOptions.length - 1}
            </LTag>
            <LTag style={{ fontSize: 11 }}>сцен: {filteredSummary.scene_count}</LTag>
            <LTag style={{ fontSize: 11 }}>планов: {filteredSummary.shot_count}</LTag>
            <LTag color="green" style={{ fontSize: 11 }}>
              клипов: {filteredSummary.clip_count}
            </LTag>
            <LTag color="blue" style={{ fontSize: 11 }}>
              кадров: {filteredSummary.frame_count}
            </LTag>
            <LTag style={{ fontSize: 11 }}>без материала: {filteredSummary.placeholder_count}</LTag>
            {filteredSummary.mock_count > 0 && (
              <LTag color="orange" style={{ fontSize: 11 }}>
                mock: {filteredSummary.mock_count}
              </LTag>
            )}
            {filteredSummary.stale_count > 0 && (
              <LTag color="warning" style={{ fontSize: 11 }}>
                устарело: {filteredSummary.stale_count}
              </LTag>
            )}
            <LTag style={{ fontSize: 11 }}>длительность: {fmtDuration(filteredSummary.total_duration_sec)}</LTag>
            {isFiltering && (
              <span data-testid="film-reel-filtered-note">
                <LTag color="purple" style={{ fontSize: 11 }}>
                  показано сцен: {filteredSummary.scene_count} из {reel.summary.scene_count}
                </LTag>
              </span>
            )}
          </LSpace>

          {isFiltering && (
            <div style={{ marginBottom: 8 }}>
              <LButton size="small" onClick={() => { setEpisode('all'); setStatus('all'); setQuery(''); }}>
                Сбросить фильтр
              </LButton>
            </div>
          )}

          {filteredScenes.length === 0 ? (
            <LEmpty description="Ничего не найдено по фильтру." />
          ) : (
            <>
              <LCard title="Предпросмотр области" size="small" style={{ marginBottom: 12 }}>
                <ReelPlayer sequence={filteredSequence} />
              </LCard>

              {episodes.map((ep) => (
                <div key={ep.chapter} data-testid="film-reel-episode" style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                    Эпизод {ep.chapter}
                    <span style={{ color: '#999', fontWeight: 400 }}>
                      {' '}
                      · сцен: {ep.scenes.length}
                    </span>
                  </div>
                  {ep.scenes.map((sc) => (
                    <SceneRow key={sc.scene_id} scene={sc} selectedKey={selectedKey} onOpenScene={onOpenScene} />
                  ))}
                </div>
              ))}

              {reel.limitations.length > 0 && (
                <div style={{ marginTop: 4 }}>
                  {reel.limitations.map((l, i) => (
                    <div key={i} style={{ fontSize: 12, color: '#999' }}>
                      {l}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

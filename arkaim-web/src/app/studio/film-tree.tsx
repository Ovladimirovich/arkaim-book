'use client';

import { useState } from 'react';
import { LEmpty, LSpin, LTag } from '@/shared/ui/light';
import { FILM_SCENE_STATUS_COLORS, FILM_SCENE_STATUS_LABELS } from './types';
import type {
  ContinuitySummaryEntryT,
  FilmEpisodeT,
  FilmT,
  WorldLinkCountsT,
} from './types';

/** Числа бейджа: подтверждённые и производные связи с миром. */
function worldBadgeText(counts?: WorldLinkCountsT): string | null {
  if (!counts) return null;
  const confirmed = counts.confirmed || 0;
  const derived = counts.derived || 0;
  if (confirmed && derived) return `мир ${confirmed}/${derived}`;
  if (confirmed) return `мир ${confirmed}`;
  if (derived) return `мир ${derived}`;
  return null;
}

/** Цвет бейджа: производное никогда не выглядит как подтверждённый факт. */
function worldBadgeColor(counts?: WorldLinkCountsT): string {
  if (!counts) return 'default';
  if ((counts.confirmed || 0) > 0) return 'success';
  return 'processing';
}

/** Подсказка бейджа: полная картина по сцене. */
function worldBadgeTitle(counts?: WorldLinkCountsT): string {
  if (!counts) return 'Связи с миром недоступны';
  return [
    'Связи с миром:',
    `подтверждено ${counts.confirmed || 0}`,
    `производных ${counts.derived || 0}`,
    `без данных ${counts.unresolved || 0}`,
  ].join(' · ');
}

/** Сводка по связям с миром для шапки дерева. */
function worldSummaryLine(scenes: FilmEpisodeT['scenes']): string | null {
  let confirmed = 0;
  let derivedOnly = 0;
  let without = 0;
  scenes.forEach((scene) => {
    const counts = scene.world_link_counts;
    if (!counts) return;
    if ((counts.confirmed || 0) > 0) confirmed += 1;
    else if ((counts.derived || 0) > 0) derivedOnly += 1;
    else without += 1;
  });
  if (!confirmed && !derivedOnly) return null;
  return `Мир: ${confirmed} сцен подтверждено · ${derivedOnly} только производные · ${without} без связей`;
}

function formatDuration(sec: number): string {
  if (!sec) return '0 с';
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m > 0 ? `${m} мин ${s} с` : `${s} с`;
}

function SceneRow({
  scene,
  selected,
  onSelect,
  continuity,
}: {
  scene: FilmEpisodeT['scenes'][number];
  selected: boolean;
  onSelect: (key: string) => void;
  continuity?: ContinuitySummaryEntryT;
}) {
  const color = FILM_SCENE_STATUS_COLORS[scene.status] || 'default';
  return (
    <button
      type="button"
      onClick={() => onSelect(`${scene.chapter}:${scene.scene_id}`)}
      title={scene.title || scene.scene_id}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        width: '100%',
        textAlign: 'left',
        padding: '6px 8px',
        borderRadius: 6,
        border: selected ? '1px solid var(--ant-color-primary, #1677ff)' : '1px solid transparent',
        background: selected ? 'rgba(22,119,255,0.08)' : 'transparent',
        cursor: 'pointer',
      }}
    >
      <span style={{ color: '#999', fontSize: 12, minWidth: 20 }}>{scene.index_in_episode + 1}</span>
      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {scene.title || scene.scene_id}
      </span>
      {continuity && continuity.mismatch_count > 0 && (
        <LTag color="warning" style={{ fontSize: 11 }}>
          связность: {continuity.mismatch_count}
        </LTag>
      )}
      {worldBadgeText(scene.world_link_counts) && (
        <LTag
          color={worldBadgeColor(scene.world_link_counts)}
          style={{ fontSize: 11 }}
          title={worldBadgeTitle(scene.world_link_counts)}
        >
          {worldBadgeText(scene.world_link_counts)}
        </LTag>
      )}
      {scene.shot_count > 0 && (
        <span style={{ fontSize: 11, color: '#999' }}>
          {scene.shot_count} план{scene.shot_count === 1 ? '' : 'ов'} · {formatDuration(scene.total_duration_sec)}
        </span>
      )}
      {scene.video_count > 0 && <LTag color="blue">видео: {scene.video_count}</LTag>}
      <LTag color={color} style={{ fontSize: 11 }}>
        {FILM_SCENE_STATUS_LABELS[scene.status]}
      </LTag>
    </button>
  );
}

export function FilmTree({
  film,
  loading,
  selectedKey,
  onSelect,
  continuity,
}: {
  film: FilmT | null | undefined;
  loading?: boolean;
  selectedKey: string | null;
  onSelect: (key: string) => void;
  continuity?: Record<string, ContinuitySummaryEntryT>;
}) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 24 }}>
        <LSpin />
      </div>
    );
  }
  if (!film || !Array.isArray(film.episodes) || film.episodes.length === 0) {
    return <LEmpty description="Сцены книги не найдены." />;
  }

  const { film: meta } = film;

  return (
    <div data-testid="film-tree">
      <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
        Фильм: {meta.episode_count} эпизод(ов) · {meta.scene_count} сцен ·{' '}
        {formatDuration(meta.total_duration_sec)}
      </div>
      {worldSummaryLine(film.episodes.flatMap((ep) => ep.scenes || [])) && (
        <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
          {worldSummaryLine(film.episodes.flatMap((ep) => ep.scenes || []))}
        </div>
      )}
      {film.episodes.map((ep) => {
        const isCollapsed = collapsed[ep.episode_id];
        return (
          <div key={ep.episode_id} style={{ marginBottom: 6 }}>
            <button
              type="button"
              onClick={() => setCollapsed((c) => ({ ...c, [ep.episode_id]: !c[ep.episode_id] }))}
              aria-expanded={!isCollapsed}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                textAlign: 'left',
                padding: '6px 8px',
                borderRadius: 6,
                border: 'none',
                background: 'rgba(0,0,0,0.03)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              <span style={{ width: 12 }}>{isCollapsed ? '▸' : '▾'}</span>
              <span style={{ flex: 1 }}>{ep.title}</span>
              <span style={{ fontSize: 11, color: '#999', fontWeight: 400 }}>
                {ep.scene_count} сцен · {formatDuration(ep.total_duration_sec)}
              </span>
            </button>
            {!isCollapsed && (
              <div style={{ marginLeft: 12, marginTop: 2 }}>
                {ep.scenes.map((scene) => (
                  <SceneRow
                    key={scene.scene_id}
                    scene={scene}
                    selected={`${scene.chapter}:${scene.scene_id}` === selectedKey}
                    onSelect={onSelect}
                    continuity={continuity?.[scene.scene_id]}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

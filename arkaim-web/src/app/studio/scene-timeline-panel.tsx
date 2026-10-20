'use client';

/**
 * SceneTimelinePanel — временная линия сцен сценария по подтверждённым эпохам.
 *
 * Источник: GET /studio/timeline (read-only). Эпоха сцены берётся только из
 * подтверждённой цепочки «одобренная связь сценарий↔книга → одобренная
 * claim-связь → каноническое событие → эпоха». Сцены без такой цепочки
 * показаны отдельным блоком с причиной: эпоха не выводится по главам и не
 * додумывается.
 */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { LEmpty, LSpin, LTag } from '@/shared/ui/light';
import { api } from '@/shared/lib/api';
import { unwrapData } from './types';
import type { SceneTimelineReportT } from './types';

function asReport(data: unknown): SceneTimelineReportT | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  if (!Array.isArray((data as SceneTimelineReportT).scenes)) return null;
  return data as SceneTimelineReportT;
}

export function SceneTimelinePanel() {
  const query = useQuery({
    queryKey: ['studio-timeline'],
    queryFn: () => api.get('/api/studio/timeline').then(unwrapData<SceneTimelineReportT>),
    staleTime: 60_000,
  });

  const report = useMemo(() => asReport(query.data), [query.data]);

  if (query.isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 12 }}>
        <LSpin />
      </div>
    );
  }

  if (query.isError) {
    return (
      <div style={{ fontSize: 12, color: '#f87171' }}>Не удалось загрузить временную линию сцен.</div>
    );
  }

  if (!report) {
    return <LEmpty description="Временная линия сцен недоступна." />;
  }

  const summary = report.summary ?? {};
  const epochs = report.epochs ?? [];
  const scenes = report.scenes ?? [];
  const titles = new Map(scenes.map((scene) => [scene.scene_id, scene.title || scene.scene_id || '']));

  if ((summary.scene_count ?? 0) === 0) {
    return <LEmpty description="Сцен в линии нет." />;
  }

  return (
    <div data-testid="scene-timeline-panel">
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
        <LTag color="blue">сцен: {summary.scene_count ?? scenes.length}</LTag>
        <LTag color="success">с подтверждённой эпохой: {summary.scenes_with_epoch ?? 0}</LTag>
        <LTag color="warning">без эпохи: {summary.scenes_without_epoch ?? 0}</LTag>
        <LTag color="geekblue">эпох: {summary.epoch_count ?? epochs.length}</LTag>
        {typeof summary.coverage === 'number' && (
          <LTag style={{ fontSize: 10 }}>покрытие: {(summary.coverage * 100).toFixed(1)} %</LTag>
        )}
      </div>

      {epochs.map((epoch) => (
        <div key={epoch.epoch_id} style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: '#e2e8f0', marginBottom: 2 }}>
            {epoch.epoch_name_ru || epoch.epoch_id}
            <span style={{ color: '#64748b' }}> · {epoch.temporal_node_id}</span>
            <span style={{ color: '#64748b' }}> · сцен: {epoch.scene_count ?? 0}</span>
          </div>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {(epoch.scene_ids ?? []).map((sceneId) => (
              <LTag key={sceneId} style={{ fontSize: 10 }} title={titles.get(sceneId) || sceneId}>
                {sceneId}
              </LTag>
            ))}
          </div>
        </div>
      ))}

      <div style={{ fontSize: 12, color: '#fbbf24', marginTop: 6 }}>
        Сцен без подтверждённой эпохи: {summary.scenes_without_epoch ?? 0} — эпоха для них не установлена.
      </div>
      {report.basis && (
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>{report.basis}</div>
      )}
      {(report.limitations ?? []).length > 0 && (
        <ul style={{ fontSize: 11, color: '#64748b', margin: '4px 0 0 16px', padding: 0 }}>
          {(report.limitations ?? []).map((limitation) => (
            <li key={limitation}>{limitation}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

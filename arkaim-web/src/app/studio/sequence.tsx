'use client';

/**
 * План сборки последовательности фильма (Фаза 4): режиссёрский просмотр
 * тайминга отрезков, разрывов (где нет готового клипа), переходов на стыках
 * и сводки исполнителей (в т.ч. флаг «смешанные исполнители»), плюс текстовый
 * план (раскадровка) для внешнего монтажа.
 *
 * Это НЕ монтаж и НЕ финальный cut. Модуль только считает и показывает
 * готовые отрезки — финальная сборка выполняется вне системы (например, в
 * DaVinci Resolve). Никакого рендера, MP4, ffmpeg и платной видеогенерации.
 *
 * Read-only проекция уже существующей ленты: порядок отрезков берётся из
 * канонических данных (геном → сцены, сценарий → планы) и не переупорядочивается.
 */

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LAlert,
  LButton,
  LCard,
  LEmpty,
  LSpace,
  LSpin,
  LTable,
  LTag,
  toast,
} from '@/shared/ui/light';
import { ExportOutlined, ReloadOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import {
  REEL_CLIP_LABELS,
  REEL_FRAME_LABELS,
  SEQUENCE_KIND_COLORS,
  SEQUENCE_KIND_LABELS,
  unwrapData,
} from './types';
import type { SequencePlanT, SequenceSegmentT } from './types';
import { fmtDuration } from './story-reel';

/** Таймкод для таймлайна: MM:SS (часы добавляются только при > 1 часа). */
function fmtStart(sec: number): string {
  const s = Math.max(0, Math.round(sec || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
}

export function FilmSequence() {
  const [showText, setShowText] = useState(false);
  const [expandedGap, setExpandedGap] = useState<string | null>(null);
  const [filterReady, setFilterReady] = useState(false);

  const sequenceQuery = useQuery({
    queryKey: ['studio-sequence'],
    queryFn: () => api.get('/api/studio/sequence').then(unwrapData<SequencePlanT>),
    staleTime: 15_000,
  });

  const plan = sequenceQuery.data;

  /** Отфильтрованная таблица: «только готово» — показывает только отрезки с video ready. */
  const displaySegments = useMemo(() => {
    if (!plan) return [];
    if (!filterReady) return plan.segments;
    return plan.segments.filter((s) => s.ready);
  }, [plan, filterReady]);

  const columns = useMemo(
    () => [
      {
        title: '#',
        key: 'index',
        width: 40,
        render: (_v: unknown, record: unknown) => (
          <span>{(record as SequenceSegmentT).index + 1}</span>
        ),
      },
      {
        title: 'Начало',
        key: 'start',
        width: 66,
        render: (_v: unknown, record: unknown) => (
          <span>{fmtStart((record as SequenceSegmentT).start_sec)}</span>
        ),
      },
      {
        title: 'Конец',
        key: 'end',
        width: 66,
        render: (_v: unknown, record: unknown) => (
          <span>{fmtStart((record as SequenceSegmentT).end_sec)}</span>
        ),
      },
      {
        title: 'Длит.',
        key: 'duration',
        width: 60,
        render: (_v: unknown, record: unknown) => (
          <span>{fmtDuration((record as SequenceSegmentT).duration_sec)}</span>
        ),
      },
      {
        title: 'Материал',
        key: 'kind',
        width: 120,
        render: (_v: unknown, record: unknown) => {
          const seg = record as SequenceSegmentT;
          return (
            <LTag color={SEQUENCE_KIND_COLORS[seg.kind]} style={{ fontSize: 10 }}>
              {SEQUENCE_KIND_LABELS[seg.kind]}
            </LTag>
          );
        },
      },
      {
        title: 'Сцена → план',
        key: 'scene',
        render: (_v: unknown, record: unknown) => {
          const seg = record as SequenceSegmentT;
          return (
            <span style={{ fontSize: 12 }}>
              <strong>эп.{seg.chapter}</strong> {seg.scene_id} → {seg.shot_id}
              {seg.scene_boundary_after && (
                <LTag color="gold" style={{ marginLeft: 6, fontSize: 10 }}>
                  граница сцен
                </LTag>
              )}
            </span>
          );
        },
      },
      {
        title: 'Статус',
        key: 'status',
        width: 110,
        render: (_v: unknown, record: unknown) => {
          const seg = record as SequenceSegmentT;
          return (
            <span style={{ fontSize: 11, color: '#888' }}>
              {seg.kind === 'clip'
                ? REEL_CLIP_LABELS[seg.clip_status]
                : REEL_FRAME_LABELS[seg.frame_status] || 'нет материала'}
            </span>
          );
        },
      },
      {
        title: 'Исполнитель',
        key: 'executor',
        width: 130,
        render: (_v: unknown, record: unknown) => {
          const seg = record as SequenceSegmentT;
          return (
            <span style={{ fontSize: 11, color: seg.executor_label ? '#666' : '#bbb' }}>
              {seg.executor_label || '—'}
            </span>
          );
        },
      },
      {
        title: 'Переход',
        key: 'transition',
        width: 90,
        render: (_v: unknown, record: unknown) => {
          const seg = record as SequenceSegmentT;
          return (
            <span style={{ fontSize: 11, color: '#999' }}>{seg.transition_to_next || '—'}</span>
          );
        },
      },
    ],
    [],
  );

  const copyPlan = async () => {
    if (!plan) return;
    try {
      await navigator.clipboard.writeText(plan.plan_text);
      toast.success('Текстовый план скопирован в буфер обмена');
    } catch {
      toast.error('Не удалось скопировать текстовый план');
    }
  };

  const exportPlan = () => {
    if (!plan) return;
    const now = new Date();
    const dateStr =
      `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-` +
      `${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
    const name = `film-sequence-${dateStr}.txt`;
    const blob = new Blob([plan.plan_text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    try {
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      toast.success(`План сохранён в «${name}»`);
    } catch {
      toast.error('Не удалось сохранить план');
    } finally {
      URL.revokeObjectURL(url);
      const el = document.querySelector<HTMLAnchorElement>('a[download]');
      if (el) el.remove();
    }
  };

  /** Экспорт плана сборки в EDL-формате (XML) для DaVinci Resolve. */
  const exportEdl = () => {
    if (!plan?.edl_xml) return;
    const now = new Date();
    const dateStr =
      `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-` +
      `${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
    const name = `film-sequence-${dateStr}.xml`;
    const blob = new Blob([plan.edl_xml], { type: 'application/xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    try {
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      toast.success(`EDL сохранён в «${name}»`);
    } catch {
      toast.error('Не удалось сохранить EDL');
    } finally {
      URL.revokeObjectURL(url);
      const el = document.querySelector<HTMLAnchorElement>('a[download]');
      if (el) el.remove();
    }
  };

  return (
    <div data-testid="film-sequence">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ fontSize: 13, color: '#666' }}>
          Режиссёрский план сборки: тайминг, разрывы, переходы и исполнители готовых отрезков.
        </span>
        <span style={{ flex: 1 }} />
        {plan && (
          <LButton size="small" icon={<ExportOutlined />} onClick={() => void copyPlan()}>
            Копировать план
          </LButton>
        )}
        {plan && (
          <LButton size="small" icon={<ExportOutlined />} onClick={() => exportPlan()}>
            Экспорт плана (TXT)
          </LButton>
        )}
        {plan?.edl_xml && (
          <LButton size="small" icon={<ExportOutlined />} onClick={() => exportEdl()}>
            Экспорт EDL (XML)
          </LButton>
        )}
        <LButton
          size="small"
          icon={<ReloadOutlined />}
          loading={sequenceQuery.isFetching}
          onClick={() => sequenceQuery.refetch()}
        >
          Обновить
        </LButton>
      </div>

      {sequenceQuery.isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <LSpin />
        </div>
      ) : sequenceQuery.isError ? (
        <LEmpty description="Не удалось загрузить план сборки." />
      ) : !plan ? (
        <LEmpty description="Сцены книги не найдены." />
      ) : (
        <div>
          <LSpace wrap style={{ marginBottom: 8 }}>
            <LTag color="geekblue" style={{ fontSize: 11 }}>
              эпизодов: {plan.summary.episode_count}
            </LTag>
            <LTag style={{ fontSize: 11 }}>сцен: {plan.summary.scene_count}</LTag>
            <LTag style={{ fontSize: 11 }}>отрезков: {plan.summary.segment_count}</LTag>
            <LTag color="green" style={{ fontSize: 11 }}>
              готово к сборке: {plan.summary.ready_count}
            </LTag>
            <LTag color="blue" style={{ fontSize: 11 }}>
              кадров: {plan.summary.frame_count}
            </LTag>
            <LTag style={{ fontSize: 11 }}>без материала: {plan.summary.placeholder_count}</LTag>
            {plan.summary.mock_count > 0 && (
              <LTag color="orange" style={{ fontSize: 11 }}>
                mock: {plan.summary.mock_count}
              </LTag>
            )}
            {plan.summary.stale_count > 0 && (
              <LTag color="warning" style={{ fontSize: 11 }}>
                устарело: {plan.summary.stale_count}
              </LTag>
            )}
            {plan.summary.gap_count > 0 && (
              <LTag color="warning" style={{ fontSize: 11 }}>
                разрывов: {plan.summary.gap_count} ({fmtDuration(plan.summary.gap_duration_sec)})
              </LTag>
            )}
            <LTag style={{ fontSize: 11 }}>всего: {fmtDuration(plan.summary.total_duration_sec)}</LTag>
            <LTag style={{ fontSize: 11 }}>
              собрано: {fmtDuration(plan.summary.assembled_duration_sec)}
            </LTag>
            {plan.executor_mixed && (
              <LTag color="warning" style={{ fontSize: 11 }}>
                смешанные исполнители: {plan.summary.executor_count}
              </LTag>
            )}
          </LSpace>

          {plan.executors.length > 0 && (
            <div data-testid="film-sequence-executors" style={{ marginBottom: 10 }}>
              <span style={{ fontSize: 11, color: '#999', marginRight: 6 }}>Исполнители готовых отрезков:</span>
              {plan.executors.map((e) => (
                <span key={e.key} data-testid="film-sequence-executor">
                  <LTag color={plan.executor_mixed ? 'warning' : 'default'} style={{ fontSize: 11 }}>
                    {e.label} · {e.count} ({fmtDuration(e.duration_sec)})
                  </LTag>
                </span>
              ))}
            </div>
          )}

          {plan.gaps.length > 0 && (
            <LCard title="Разрывы (нет готового клипа)" size="small" style={{ marginBottom: 12 }}>
              {plan.gaps.map((gap) => {
                const open = expandedGap === `${gap.start_index}-${gap.end_index}`;
                return (
                  <div key={`${gap.start_index}-${gap.end_index}`}>
                    <div
                      data-testid="film-sequence-gap"
                      onClick={() => setExpandedGap(open ? null : `${gap.start_index}-${gap.end_index}`)}
                      style={{
                        fontSize: 12,
                        color: '#666',
                        cursor: 'pointer',
                        padding: '4px 6px',
                        borderRadius: 6,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        userSelect: 'none',
                        background: open ? 'rgba(127,127,127,0.06)' : 'transparent',
                      }}
                    >
                      <span style={{ fontSize: 10 }}>{open ? '▼' : '▶'}</span>
                      <LTag color="warning" style={{ fontSize: 10 }}>
                        отрезки {gap.start_index + 1}–{gap.end_index + 1} ({gap.segment_count})
                      </LTag>{' '}
                      {fmtStart(gap.start_sec)} → {fmtStart(gap.end_sec)} ({fmtDuration(gap.duration_sec)}) ·{' '}
                      {gap.kinds.map((k) => SEQUENCE_KIND_LABELS[k]).join(', ')}
                    </div>
                    {open && (
                      <div
                        data-testid="film-sequence-gap-details"
                        style={{ fontSize: 12, padding: '4px 6px 6px 24px', color: '#888' }}
                      >
                        {gap.shot_ids.map((sid) => (
                          <div key={sid} style={{ padding: '2px 0' }}>
                            {sid} · сцена {gap.scene_ids[0]}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </LCard>
          )}

          <div style={{ marginBottom: 8 }} data-testid="film-sequence-filter-ready">
            <LButton size="small" type={filterReady ? 'primary' : 'default'} onClick={() => setFilterReady((v) => !v)}>
              {filterReady ? 'Показать все отрезки' : 'Только готовые'}
            </LButton>
          </div>

          <LTable
            columns={columns}
            dataSource={displaySegments}
            rowKey={(record) => String((record as SequenceSegmentT).index)}
            size="small"
            pagination={false}
          />

          <div style={{ marginTop: 8 }}>
            <LButton size="small" type={showText ? 'primary' : 'default'} onClick={() => setShowText((v) => !v)}>
              {showText ? 'Скрыть текстовый план' : 'Показать текстовый план'}
            </LButton>
            {showText && (
              <pre
                data-testid="film-sequence-plan-text"
                style={{
                  marginTop: 8,
                  padding: 12,
                  background: 'rgba(127,127,127,0.08)',
                  borderRadius: 8,
                  fontSize: 12,
                  lineHeight: 1.5,
                  overflowX: 'auto',
                  whiteSpace: 'pre',
                }}
              >
                {plan.plan_text}
              </pre>
            )}
          </div>

          {plan.limitations.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {plan.limitations.map((l, i) => (
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
        message="Это план сборки, а не монтаж."
        description="Карточка только считает и показывает готовые отрезки (тайминг, разрывы, переходы, исполнители). Финальная сборка фильма выполняется вне системы — например, в DaVinci Resolve. Здесь нет рендера, MP4 и ffmpeg; план готовится для переноса в монтажную программу."
      />
    </div>
  );
}

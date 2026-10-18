'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { LAlert, LButton, LEmpty, LInput, LModal, LSpace, LSpin, LTag, toast } from '@/shared/ui/light';
import { api } from '@/shared/lib/api';
import {
  CONTINUITY_FIELD_LABELS,
  CONTINUITY_RELATION_LABELS,
  CONTINUITY_STATUS_COLORS,
  CONTINUITY_STATUS_LABELS,
  unwrapData,
} from './types';
import type {
  ContinuityFindingT,
  ContinuityLinkT,
  MatchContextT,
  SceneContinuityReportT,
  StudioSessionT,
} from './types';

type Props = {
  session: StudioSessionT;
};

/** Мок-данные старых тестов отдают массив — отчёт обязан быть объектом. */
function asReport(data: unknown): SceneContinuityReportT | null {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  if (!Array.isArray((data as SceneContinuityReportT).links)) return null;
  return data as SceneContinuityReportT;
}

function statusTag(status: string) {
  return (
    <LTag color={CONTINUITY_STATUS_COLORS[status] || 'default'}>
      {CONTINUITY_STATUS_LABELS[status] || status}
    </LTag>
  );
}

function formatValue(v: string): string {
  return v && v.trim() ? v : '—';
}

function FieldLabel({ field }: { field: string }) {
  return <span style={{ color: '#999' }}>{CONTINUITY_FIELD_LABELS[field] || field}</span>;
}

function FindingRow({ finding }: { finding: ContinuityFindingT }) {
  const warning = finding.severity === 'warning';
  return (
    <div
      data-testid="continuity-finding"
      style={{
        padding: '6px 8px',
        borderRadius: 6,
        borderLeft: `3px solid ${warning ? '#ff4d4f' : '#1677ff'}`,
        background: warning ? 'rgba(255,77,79,0.05)' : 'rgba(22,119,255,0.05)',
        marginBottom: 4,
      }}
    >
      <div style={{ fontSize: 13 }}>{finding.message}</div>
      <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
        <FieldLabel field={finding.field} />
        {finding.subject ? ` · ${finding.subject}` : ''}: {formatValue(finding.from_value)} →{' '}
        {formatValue(finding.to_value)}
        {finding.certainty === 'candidate' && <LTag style={{ marginLeft: 6, fontSize: 10 }}>предположение</LTag>}
      </div>
    </div>
  );
}

function ClipBoundary({ link }: { link: ContinuityLinkT }) {
  const cb = link.clip_boundary;
  if (!cb) return null;
  return (
    <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
      Контракт связи клипов: end frame {cb.end_frame_asset_id || '—'} → start frame{' '}
      {cb.start_frame_asset_id || '—'} · {cb.status === 'declared' ? 'объявлен' : 'не объявлен'}
    </div>
  );
}

function LinkRow({
  link,
  onWaive,
  onRemove,
  busy,
}: {
  link: ContinuityLinkT;
  onWaive: (link: ContinuityLinkT) => void;
  onRemove: (decisionId: string) => void;
  busy: boolean;
}) {
  const decision = link.decision;
  const stale = !!decision?.stale;
  return (
    <div
      data-testid="continuity-link"
      style={{
        border: '1px solid var(--card-border, #eee)',
        borderRadius: 8,
        padding: 10,
        marginBottom: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 13 }}>
          {CONTINUITY_RELATION_LABELS[link.relation] || link.relation}
        </strong>
        {statusTag(link.status)}
        {link.certainty === 'candidate' && <LTag style={{ fontSize: 11 }}>кандидат</LTag>}
        <span style={{ flex: 1 }} />
        {decision ? (
          <LSpace>
            {stale && <LTag color="warning">решение устарело</LTag>}
            <LButton size="small" disabled={busy} onClick={() => onRemove(decision.decision_id)}>
              Снять решение
            </LButton>
          </LSpace>
        ) : (
          link.status === 'mismatch' && (
            <LButton size="small" type="primary" disabled={busy} onClick={() => onWaive(link)}>
              Разрешить отличие
            </LButton>
          )
        )}
      </div>

      {link.reason && <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{link.reason}</div>}
      {decision?.note && (
        <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>Решение: {decision.note}</div>
      )}

      {link.findings.length > 0 ? (
        <div style={{ marginTop: 6 }}>
          {link.findings.map((f, i) => (
            <FindingRow key={`${f.field}-${i}`} finding={f} />
          ))}
        </div>
      ) : (
        <div style={{ fontSize: 12, color: '#999', marginTop: 6 }}>
          {link.status === 'unchecked'
            ? 'Сопоставимых данных нет — сравнение не выполнялось.'
            : 'Отличий не найдено.'}
        </div>
      )}

      <ClipBoundary link={link} />
    </div>
  );
}

function MatchContextPreview({
  session,
  open,
  onClose,
  onApply,
  onRevoke,
  busy,
}: {
  session: StudioSessionT;
  open: boolean;
  onClose: () => void;
  onApply: () => void;
  onRevoke: () => void;
  busy: boolean;
}) {
  const query = useQuery({
    queryKey: ['studio-match-context', session.session_id],
    queryFn: () =>
      api
        .get(`/api/studio/${session.session_id}/continuity/match-context`)
        .then(unwrapData<MatchContextT>),
    enabled: open,
  });

  const data = query.data;
  const canApply = !!data?.available;
  const applied = !!data?.applied;

  return (
    <LModal
      open={open}
      title="Согласовать со сценой"
      width={720}
      onCancel={onClose}
      footer={
        <LSpace>
          <LButton onClick={onClose}>Закрыть</LButton>
          {canApply && applied && (
            <LButton danger loading={busy} onClick={onRevoke}>
              Отменить применение
            </LButton>
          )}
          {canApply && !applied && (
            <LButton type="primary" loading={busy} onClick={onApply}>
              Применить к сцене
            </LButton>
          )}
        </LSpace>
      }
    >
      {query.isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <LSpin />
        </div>
      ) : !data || !data.available ? (
        <LEmpty description={data?.reason || 'Предпросмотр недоступен.'} />
      ) : (
        <div data-testid="match-context">
          <LAlert
            type={applied ? 'success' : data.applied_stale ? 'warning' : 'info'}
            showIcon
            message={
              applied
                ? 'Перенос применён к сцене.'
                : data.applied_stale
                  ? 'Ранее применённый перенос устарел.'
                  : 'Предпросмотр. Ничего не изменено автоматически.'
            }
            description={data.note}
            style={{ marginBottom: 12 }}
          />

          <div style={{ fontSize: 13, marginBottom: 8 }}>
            Из сцены <strong>{data.from_scene_id}</strong> в сцену <strong>{data.to_scene_id}</strong>
          </div>

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>Что можно перенести</div>
            {Object.entries(data.constraints || {}).length === 0 ? (
              <span style={{ color: '#999', fontSize: 12 }}>Нет известных характеристик для переноса.</span>
            ) : (
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
                {Object.entries(data.constraints || {}).map(([key, value]) => (
                  <li key={key}>
                    <FieldLabel field={key} />: {Array.isArray(value) ? value.join(', ') : String(value)}
                    {data.sources?.[key] ? (
                      <span style={{ color: '#999' }}> (источник: {data.sources[key]})</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>Что изменится в промптах</div>
            {(data.prompt_changes || []).length === 0 ? (
              <span style={{ color: '#999', fontSize: 12 }}>Предпросмотр промптов недоступен.</span>
            ) : (
              (data.prompt_changes || []).map((pc) => (
                <div key={pc.shot_id} style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 12, color: '#666' }}>
                    План {pc.shot_id} {pc.changed ? '— изменится' : '— без изменений'}
                  </div>
                  {pc.changed && (
                    <div style={{ fontSize: 12 }}>
                      <div style={{ color: '#999' }}>до: {pc.before}</div>
                      <div style={{ color: '#1677ff' }}>после: {pc.after}</div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          <div>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>Что останется отличием</div>
            {(data.remaining_differences || []).length === 0 ? (
              <span style={{ color: '#999', fontSize: 12 }}>Отличий не обнаружено.</span>
            ) : (
              (data.remaining_differences || []).map((f, i) => <FindingRow key={`${f.field}-${i}`} finding={f} />)
            )}
          </div>

          {(data.limitations || []).length > 0 && (
            <div style={{ marginTop: 12 }}>
              {data.limitations?.map((l, i) => (
                <div key={i} style={{ fontSize: 12, color: '#999' }}>
                  {l}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </LModal>
  );
}

export function ContinuityPanel({ session }: Props) {
  const queryClient = useQueryClient();
  const [previewOpen, setPreviewOpen] = useState(false);
  const [note, setNote] = useState('');

  const query = useQuery({
    queryKey: ['studio-continuity', session.session_id],
    queryFn: () =>
      api
        .get(
          `/api/studio/scenes/${encodeURIComponent(session.scene_id)}/continuity?chapter=${session.chapter}`,
        )
        .then(unwrapData<SceneContinuityReportT>),
  });

  const report = useMemo(() => asReport(query.data), [query.data]);

  const matchQuery = useQuery({
    queryKey: ['studio-match-context', session.session_id],
    queryFn: () =>
      api
        .get(`/api/studio/${session.session_id}/continuity/match-context`)
        .then(unwrapData<MatchContextT>),
  });
  const matchCtx = matchQuery.data;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['studio-continuity', session.session_id] });
    queryClient.invalidateQueries({ queryKey: ['studio-continuity-summary'] });
    queryClient.invalidateQueries({ queryKey: ['studio-match-context', session.session_id] });
  };

  const waiveMutation = useMutation({
    mutationFn: (link: ContinuityLinkT) =>
      api.post('/api/studio/continuity/decisions', {
        link_key: link.link_key,
        basis: link.basis,
        session_id: session.session_id,
        note,
      }),
    onSuccess: () => {
      toast.success('Отличие разрешено режиссёром');
      setNote('');
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось сохранить решение: ${err.message}`),
  });

  const removeMutation = useMutation({
    mutationFn: (decisionId: string) => api.delete(`/api/studio/continuity/decisions/${decisionId}`),
    onSuccess: () => {
      toast.success('Решение снято');
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось снять решение: ${err.message}`),
  });

  const applyMutation = useMutation({
    mutationFn: () => api.post(`/api/studio/${session.session_id}/continuity/apply`, { note }),
    onSuccess: () => {
      toast.success('Перенос ограничений применён к сцене');
      setNote('');
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось применить перенос: ${err.message}`),
  });

  const revokeMutation = useMutation({
    mutationFn: () => api.delete(`/api/studio/${session.session_id}/continuity/apply`),
    onSuccess: () => {
      toast.success('Применение переноса снято');
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось снять перенос: ${err.message}`),
  });

  if (query.isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 24 }}>
        <LSpin />
      </div>
    );
  }
  if (query.isError) {
    return <LEmpty description="Не удалось загрузить связность сцены." />;
  }
  if (!report) {
    return <LEmpty description="Связность недоступна для этой сцены." />;
  }

  const busy = waiveMutation.isPending || removeMutation.isPending || applyMutation.isPending || revokeMutation.isPending;
  const applied = !!matchCtx?.applied;
  const appliedStale = !!matchCtx?.applied_stale;
  const canApply = !!matchCtx?.available && !!matchCtx?.to_scene_id;

  return (
    <div data-testid="continuity-panel">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
        <span style={{ fontSize: 13 }}>Состояние сцены:</span>
        {statusTag(report.overall_status)}
        {applied && <LTag color="processing">перенос применён</LTag>}
        {!applied && appliedStale && <LTag color="warning">перенос устарел</LTag>}
        <span style={{ flex: 1 }} />
        {canApply && !applied && (
          <LButton size="small" type="primary" disabled={busy} onClick={() => applyMutation.mutate()}>
            Применить к сцене
          </LButton>
        )}
        {applied && (
          <LButton size="small" danger disabled={busy} onClick={() => revokeMutation.mutate()}>
            Отменить применение
          </LButton>
        )}
        <LButton size="small" onClick={() => setPreviewOpen(true)}>
          Согласовать со сценой
        </LButton>
      </div>

      {report.links.some((l) => l.status === 'mismatch') && (
        <LInput
          placeholder="Комментарий к решению (необязательно)"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          style={{ marginBottom: 8 }}
        />
      )}

      {report.links.length === 0 ? (
        <LEmpty description="Связей для проверки нет." />
      ) : (
        report.links.map((link) => (
          <LinkRow
            key={link.link_key}
            link={link}
            busy={busy}
            onWaive={(l) => waiveMutation.mutate(l)}
            onRemove={(id) => removeMutation.mutate(id)}
          />
        ))
      )}

      {report.limitations.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {report.limitations.map((l, i) => (
            <div key={i} style={{ fontSize: 12, color: '#999' }}>
              {l}
            </div>
          ))}
        </div>
      )}

      <MatchContextPreview
        session={session}
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        onApply={() => applyMutation.mutate()}
        onRevoke={() => revokeMutation.mutate()}
        busy={busy}
      />
    </div>
  );
}

'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LAlert,
  LButton,
  LCard,
  LModal,
  LSelect,
  LSpace,
  LSpin,
  LTag,
  toast,
} from '@/shared/ui/light';
import { api } from '@/shared/lib/api';
import { assetFileUrl, unwrapData } from './types';
import type {
  AffectedArtifactT,
  AppliedShotT,
  ArtDirectionApplyT,
  ExecutorInfoT,
  JobAsset,
  PreparedUpdateT,
  StaleVideoT,
  StudioSessionT,
} from './types';

type Props = {
  session: StudioSessionT;
};

/** Подготовленное задание + его исполнитель (ответ GET prepared-updates). */
type PreparedListT = {
  prepared_updates: PreparedUpdateT[];
  executors: Record<string, ExecutorInfoT>;
};

const FRAME_STATUS_META: Record<string, { label: string; color: string }> = {
  current: { label: 'актуален', color: 'success' },
  needs_update: { label: 'требует обновления', color: 'orange' },
  prepared_for_update: { label: 'подготовлен к обновлению', color: 'blue' },
  new_variant: { label: 'новый вариант', color: 'purple' },
  approved: { label: 'утверждён', color: 'success' },
};

const PREPARED_STATUS_META: Record<string, { label: string; color: string }> = {
  prepared: { label: 'подготовлен', color: 'blue' },
  generating: { label: 'генерация…', color: 'processing' },
  done: { label: 'вариант готов', color: 'purple' },
  approved: { label: 'утверждён', color: 'success' },
  cancelled: { label: 'отменён', color: 'default' },
};

function FrameStatusTag({ status }: { status?: string }) {
  const meta = FRAME_STATUS_META[status || ''] || { label: status || '—', color: 'default' };
  return (
    <span data-testid={`frame-status-${status || 'unknown'}`}>
      <LTag color={meta.color as 'default'} style={{ fontSize: 11 }}>
        {meta.label}
      </LTag>
    </span>
  );
}

function PromptBox({ label, text }: { label: string; text: string }) {
  return (
    <div style={{ flex: '1 1 260px', minWidth: 220 }}>
      <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>{label}</div>
      <div
        style={{
          fontSize: 11,
          whiteSpace: 'pre-wrap',
          maxHeight: 120,
          overflow: 'auto',
          padding: 6,
          borderRadius: 6,
          background: 'rgba(0,0,0,0.04)',
          border: '1px solid var(--card-border)',
        }}
      >
        {text || '—'}
      </div>
    </div>
  );
}

/** Размер кадра для image-jobs: вертикальный пресет аспекта → вертикальный размер. */
function sizeForAspect(aspect: unknown): string {
  const a = String(aspect || '');
  if (a.startsWith('9:1') || a.startsWith('2:3')) return '576x1024';
  return '1024x1024';
}

/**
 * Панель «Затронутые кадры» — управляемое обновление (OWNER-GO):
 * выбрать затронутый кадр → «Подготовить обновление» (черновик задания,
 * БЕЗ генерации) → выбрать исполнителя → «Сгенерировать» (штатный
 * image-jobs, по умолчанию mock) → сравнить старый↔новый → «Утвердить»
 * (кадр шота + кадр-основа сцены). Массовой генерации нет, платных
 * исполнителей нет, старые ассеты не удаляются.
 */
export function AffectedPanel({ session }: Props) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [comparePrepId, setComparePrepId] = useState<string | null>(null);
  /** Шот для кадров без привязки (выбор в карточке; дефолт — первый план). */
  const [shotChoice, setShotChoice] = useState<Record<string, string>>({});

  const applyQuery = useQuery({
    queryKey: ['studio-apply', session.session_id],
    queryFn: () =>
      api
        .get(`/api/studio/${session.session_id}/art-direction/apply`)
        .then(unwrapData<ArtDirectionApplyT>),
    staleTime: 15_000,
  });

  const hasGenerating = (applyQuery.data?.prepared_updates || []).some(
    (p) => p.status === 'generating',
  );
  const preparedQuery = useQuery({
    queryKey: ['studio-prepared', session.session_id],
    queryFn: () =>
      api
        .get(`/api/studio/${session.session_id}/prepared-updates`)
        .then(unwrapData<PreparedListT>),
    staleTime: 10_000,
    refetchInterval: hasGenerating ? 3000 : false,
  });

  const apply = applyQuery.data;
  const affected = apply?.affected_artifacts || [];
  const shots: AppliedShotT[] = useMemo(() => apply?.shots || [], [apply]);
  const staleVideos: StaleVideoT[] = apply?.stale_videos || [];
  const preparedList = useMemo(() => preparedQuery.data?.prepared_updates || [], [preparedQuery.data]);
  const executors = preparedQuery.data?.executors || {};

  const shotsById = useMemo(() => new Map(shots.map((s) => [s.shot_id, s])), [shots]);
  const preparedById = useMemo(() => new Map(preparedList.map((p) => [p.prepared_id, p])), [preparedList]);
  const sourcePrepared = useMemo(
    () => new Map(preparedList.filter((p) => p.source_asset_id).map((p) => [p.source_asset_id!, p])),
    [preparedList],
  );

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['studio-apply', session.session_id] });
    queryClient.invalidateQueries({ queryKey: ['studio-prepared', session.session_id] });
    queryClient.invalidateQueries({ queryKey: ['studio-session', session.session_id] });
    queryClient.invalidateQueries({ queryKey: ['studio-video-assets'] });
  };

  const defaultShotId = shots[0]?.shot_id || '';
  const shotFor = (a: AffectedArtifactT): string =>
    a.shot_id || sourcePrepared.get(a.asset_id)?.shot_id || shotChoice[a.asset_id] || defaultShotId;

  // ── Подготовка одного обновления (черновик, без генерации) ──
  const prepare = useMutation({
    mutationFn: (args: { shotId: string; sourceAssetId?: string }) =>
      api
        .post(`/api/studio/${session.session_id}/prepared-updates`, {
          shot_id: args.shotId,
          source_asset_id: args.sourceAssetId ?? null,
          backend: 'mock',
        })
        .then(unwrapData<{ prepared: PreparedUpdateT }>),
    onSuccess: (data) => {
      toast.success(`Задание подготовлено для плана ${data.prepared.shot_id} — генерация не запускалась`);
      invalidateAll();
    },
    onError: (err: Error) => toast.error(`Не удалось подготовить обновление: ${err.message}`),
  });

  // ── Массовая подготовка (без генерации) ──
  const [summary, setSummary] = useState<string[] | null>(null);
  const massPrepare = useMutation({
    mutationFn: async (items: AffectedArtifactT[]) => {
      const lines: string[] = [];
      const errors: string[] = [];
      for (const a of items) {
        const shotId = shotFor(a);
        if (!shotId) {
          errors.push(`${a.title || a.asset_id}: не выбран план`);
          continue;
        }
        try {
          await api.post(`/api/studio/${session.session_id}/prepared-updates`, {
            shot_id: shotId,
            source_asset_id: a.asset_id,
            backend: 'mock',
          });
          const shot = shotsById.get(shotId);
          lines.push(`${a.title || a.asset_id} → план ${shotId} (${shot?.shot_type || ''})`);
        } catch (err) {
          errors.push(`${a.title || a.asset_id}: ${(err as Error).message}`);
        }
      }
      return { lines, errors };
    },
    onSuccess: ({ lines, errors }) => {
      setSelected(new Set());
      setSummary(lines);
      if (lines.length > 0) {
        toast.success(`Подготовлено заданий: ${lines.length} (без генерации)`);
      }
      if (errors.length > 0) {
        toast.error(`Не подготовлено: ${errors.length} — ${errors[0]}`);
      }
      invalidateAll();
    },
  });

  const toggleSelect = (assetId: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(assetId)) next.delete(assetId);
      else next.add(assetId);
      return next;
    });
  };

  const selectable = affected.filter(
    (a) =>
      a.asset_type === 'image' &&
      (a.frame_status === 'needs_update' || a.frame_status === 'prepared_for_update') &&
      !sourcePrepared.get(a.asset_id),
  );

  const needsCount = affected.filter((a) => a.frame_status === 'needs_update' || a.frame_status === 'prepared_for_update').length;
  const newVariants = preparedList.filter((p) => p.status === 'done' || p.status === 'approved');

  if (applyQuery.isLoading || preparedQuery.isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 24 }}>
        <LSpin />
      </div>
    );
  }

  if (applyQuery.isError) {
    return <LAlert type="error" showIcon message="Не удалось загрузить затронутые кадры" description={(applyQuery.error as Error).message} />;
  }

  return (
    <div data-testid="affected-panel">
      <LSpace wrap style={{ marginBottom: 12 }}>
        <span data-testid="affected-needs-count">
          <LTag color="orange" style={{ fontSize: 11 }}>
            требуют обновления: {needsCount}
          </LTag>
        </span>
        <LTag color="blue" style={{ fontSize: 11 }}>
          заданий подготовлено: {preparedList.filter((p) => p.status === 'prepared' || p.status === 'generating').length}
        </LTag>
        <LTag color="purple" style={{ fontSize: 11 }}>
          новых вариантов: {newVariants.length}
        </LTag>
        {staleVideos.length > 0 && (
          <LTag color="warning" style={{ fontSize: 11 }}>
            видео на старом кадре: {staleVideos.length}
          </LTag>
        )}
      </LSpace>

      {summary && summary.length > 0 && (
        <LCard size="small" style={{ marginBottom: 12 }} title="Подготовленные изменения (сводка)">
          <div data-testid="mass-summary">
            {summary.map((line) => (
              <div key={line} style={{ fontSize: 12 }}>
                · {line}
              </div>
            ))}
            <div style={{ fontSize: 11, color: '#999', marginTop: 6 }}>
              Генерация не запускалась — каждое задание запускается отдельно кнопкой «Сгенерировать».
            </div>
            <LButton size="small" style={{ marginTop: 6 }} onClick={() => setSummary(null)}>
              Скрыть сводку
            </LButton>
          </div>
        </LCard>
      )}

      {selectable.length > 0 && (
        <LCard
          size="small"
          style={{ marginBottom: 12 }}
          title="Массовая подготовка (без генерации)"
          extra={
            <LSpace wrap>
              <span style={{ fontSize: 12 }}>выбрано: {selected.size}</span>
              <LButton
                size="small"
                type="primary"
                disabled={selected.size === 0 || massPrepare.isPending || prepare.isPending}
                loading={massPrepare.isPending}
                onClick={() =>
                  massPrepare.mutate(selectable.filter((a) => selected.has(a.asset_id)))
                }
              >
                Подготовить обновление ({selected.size})
              </LButton>
              <LButton size="small" disabled={selected.size === 0} onClick={() => setSelected(new Set())}>
                Отменить выбор
              </LButton>
            </LSpace>
          }
        >
          <div style={{ fontSize: 11, color: '#999', marginBottom: 8 }}>
            Отметьте кадры — будет созданы черновики заданий (промпт, правила, референсы) со
            сводкой изменений. Массовой генерации нет: каждый вариант генерируется и
            утверждается отдельно.
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {selectable.map((a) => (
              <label key={a.asset_id} style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>
                <input
                  type="checkbox"
                  checked={selected.has(a.asset_id)}
                  onChange={() => toggleSelect(a.asset_id)}
                  data-testid={`affected-check-${a.asset_id}`}
                />
                <span>{a.title || a.asset_id}</span>
                <span style={{ color: '#999' }}>
                  план: {shotFor(a) || '—'}
                </span>
                {!a.shot_id && shots.length > 1 && (
                  <select
                    value={shotFor(a)}
                    onChange={(e) => setShotChoice((prev) => ({ ...prev, [a.asset_id]: e.target.value }))}
                    style={{ fontSize: 11 }}
                    data-testid={`affected-shot-select-${a.asset_id}`}
                  >
                    {shots.map((s) => (
                      <option key={s.shot_id} value={s.shot_id}>
                        {s.shot_index}. {s.shot_type} ({s.shot_id})
                      </option>
                    ))}
                  </select>
                )}
              </label>
            ))}
          </div>
        </LCard>
      )}

      {affected.length === 0 && (
        <LAlert
          type="success"
          showIcon
          message="Затронутых кадров нет"
          description="Все подготовленные результаты соответствуют текущим правилам фильма."
        />
      )}

      {affected.slice(0, 30).map((a) => (
        <AffectedCard
          key={a.asset_id}
          affected={a}
          shots={shots}
          shotId={shotFor(a)}
          onShotChange={(v) => setShotChoice((prev) => ({ ...prev, [a.asset_id]: v }))}
          prepared={a.prepared ? preparedById.get(a.prepared.prepared_id) : sourcePrepared.get(a.asset_id)}
          onPrepare={() => {
            const shotId = shotFor(a);
            if (!shotId) {
              toast.error('Выберите план сценария для этого кадра');
              return;
            }
            prepare.mutate({ shotId, sourceAssetId: a.asset_id });
          }}
          preparing={prepare.isPending}
          onCompare={a.prepared || sourcePrepared.get(a.asset_id) ? () => setComparePrepId((a.prepared || sourcePrepared.get(a.asset_id))!.prepared_id) : undefined}
        />
      ))}
      {affected.length > 30 && (
        <div style={{ fontSize: 11, color: '#999', marginBottom: 8 }}>
          …и ещё {affected.length - 30} ранее подготовленных результатов этой сцены
        </div>
      )}

      {preparedList.filter((p) => p.status !== 'cancelled').length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Подготовленные задания</div>
          {preparedList
            .filter((p) => p.status !== 'cancelled')
            .map((p) => (
              <PreparedCard
                key={p.prepared_id}
                prepared={preparedById.get(p.prepared_id) || p}
                session={session}
                executors={executors}
                source={affected.find((a) => a.asset_id === p.source_asset_id)}
                onChanged={invalidateAll}
                onCompare={() => setComparePrepId(p.prepared_id)}
              />
            ))}
        </div>
      )}

      {staleVideos.length > 0 && (
        <LCard size="small" style={{ marginTop: 16 }} title="Видео на предыдущем кадре (требуют обновления)">
          <div data-testid="stale-videos">
            {staleVideos.map((v) => (
              <div key={v.asset_id} style={{ marginBottom: 8, fontSize: 12 }}>
                <LSpace wrap>
                  <LTag color="purple" style={{ fontSize: 11 }}>
                    видео
                  </LTag>
                  <strong>{v.title || v.asset_id}</strong>
                  <a href={assetFileUrl(v.asset_id)} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>
                    открыть
                  </a>
                  <span style={{ fontSize: 11, color: '#999' }}>
                    связано с кадром: {v.reference_image_id}
                  </span>
                </LSpace>
                <div style={{ color: '#999', fontSize: 11 }}>{v.reason} — старое видео не удаляется</div>
              </div>
            ))}
            <LAlert
              type="info"
              showIcon
              message="Связь видео ↔ исходный кадр сохраняется"
              description="После утверждения нового кадра видео помечается как требующее обновления; новое видео запускается отдельно (кнопка «Сгенерировать видео» в панели видео)."
            />
          </div>
        </LCard>
      )}

      {comparePrepId && (
        <CompareModal
          prepared={preparedById.get(comparePrepId)!}
          source={affected.find((a) => a.asset_id === (preparedById.get(comparePrepId)?.source_asset_id || null))}
          sceneApprovedId={apply?.scene?.approved_image_asset_id || null}
          onClose={() => setComparePrepId(null)}
          onApproved={() => {
            setComparePrepId(null);
            invalidateAll();
          }}
        />
      )}
    </div>
  );
}

// ── Карточка затронутого кадра ──────────────────────────────────

function AffectedCard({
  affected,
  shots,
  shotId,
  onShotChange,
  prepared,
  onPrepare,
  preparing,
  onCompare,
}: {
  affected: AffectedArtifactT;
  shots: AppliedShotT[];
  shotId: string;
  onShotChange: (shotId: string) => void;
  prepared?: PreparedUpdateT;
  onPrepare: () => void;
  preparing: boolean;
  onCompare?: () => void;
}) {
  const shot = shots.find((s) => s.shot_id === shotId) || affected.shot;
  const applied = shot?.applied;

  return (
    <LCard
      size="small"
      style={{ marginBottom: 10 }}
      title={
        <LSpace wrap>
          <span>{affected.title || affected.asset_id}</span>
          <FrameStatusTag status={affected.frame_status} />
          {affected.asset_type === 'video' && (
            <LTag color="purple" style={{ fontSize: 11 }}>
              видео
            </LTag>
          )}
        </LSpace>
      }
      extra={
        <LSpace wrap>
          <a href={assetFileUrl(affected.asset_id)} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>
            открыть кадр
          </a>
          {onCompare && (
            <LButton size="small" onClick={onCompare}>
              Сравнить
            </LButton>
          )}
        </LSpace>
      }
    >
      <div data-testid={`affected-card-${affected.asset_id}`}>
        <div style={{ fontSize: 11, color: '#999', marginBottom: 6 }}>
          причина: {affected.reasons.join('; ')}
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
          <img
            src={assetFileUrl(affected.asset_id)}
            alt={affected.title || affected.asset_id}
            style={{ width: 120, borderRadius: 6, border: '1px solid var(--card-border)' }}
          />
          <div style={{ flex: '1 1 240px', minWidth: 200 }}>
            <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>план сценария</div>
            <LSpace wrap style={{ marginBottom: 6 }}>
              {shot ? (
                <>
                  <LTag style={{ fontSize: 11 }}>
                    {shot.shot_index}. {shot.shot_type}
                  </LTag>
                  <span style={{ fontSize: 11, color: '#999' }}>{shot.shot_id}</span>
                  {shot.approved_image_asset_id === affected.asset_id && (
                    <LTag color="success" style={{ fontSize: 11 }}>
                      утверждённый кадр плана
                    </LTag>
                  )}
                </>
              ) : (
                <span style={{ fontSize: 11, color: '#c00' }}>
                  кадр без привязки к плану — выберите план для обновления
                </span>
              )}
            </LSpace>
            {shots.length > 0 && (
              <select
                value={shotId}
                onChange={(e) => onShotChange(e.target.value)}
                style={{ fontSize: 11, width: '100%' }}
                data-testid={`card-shot-select-${affected.asset_id}`}
              >
                {shots.map((s) => (
                  <option key={s.shot_id} value={s.shot_id}>
                    {s.shot_index}. {s.shot_type} ({s.shot_id})
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
          <PromptBox label="промпт, с которым кадр сгенерирован" text={affected.prompt_used || ''} />
          <PromptBox label="новый итоговый промпт плана (по текущим правилам)" text={shot?.resolved_prompt || ''} />
        </div>

        {applied && (
          <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>
            применяются правила: стиль «{applied.style_preset}» (rev {applied.revision}) · палитра:{' '}
            {(applied.palette || []).join(', ') || '—'} · персонажи:{' '}
            {(applied.characters || []).map((c) => c.name || c.knowledge_key).join(', ') || '—'} ·
            локация: {applied.location?.name || '—'}
          </div>
        )}
        {shot && Object.keys(shot.local_overrides || {}).length > 0 && (
          <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>
            локальные переопределения плана: {Object.keys(shot.local_overrides).join(', ')}
          </div>
        )}

        <LSpace wrap>
          {prepared ? (
            <LTag color="blue" style={{ fontSize: 11 }}>
              задание {PREPARED_STATUS_META[prepared.status]?.label || prepared.status}
            </LTag>
          ) : (
            affected.asset_type === 'image' && (
              <span data-testid={`prepare-${affected.asset_id}`}>
                <LButton
                  size="small"
                  type="primary"
                  disabled={preparing || !shotId}
                  loading={preparing}
                  onClick={onPrepare}
                >
                  Подготовить обновление
                </LButton>
              </span>
            )
          )}
          <span style={{ fontSize: 11, color: '#999' }}>
            «Подготовить» собирает задание (промпт/правила/референсы) — генерация не запускается.
          </span>
        </LSpace>
      </div>
    </LCard>
  );
}

// ── Карточка подготовленного задания ────────────────────────────

function PreparedCard({
  prepared,
  session,
  executors,
  source,
  onChanged,
  onCompare,
}: {
  prepared: PreparedUpdateT;
  session: StudioSessionT;
  executors: Record<string, ExecutorInfoT>;
  source?: AffectedArtifactT;
  onChanged: () => void;
  onCompare: () => void;
}) {
  const queryClient = useQueryClient();
  const executor = executors[prepared.backend];
  const statusMeta = PREPARED_STATUS_META[prepared.status] || { label: prepared.status, color: 'default' };

  // Поллинг статуса нового варианта через СУЩЕСТВУЮЩИЙ GET /book/assets/{id}.
  const assetQuery = useQuery({
    queryKey: ['studio-asset', prepared.new_asset_id],
    queryFn: () => api.get(`/book/assets/${prepared.new_asset_id}`).then(unwrapData<JobAsset>),
    enabled: !!prepared.new_asset_id && (prepared.status === 'generating' || prepared.status === 'done'),
    refetchInterval: prepared.status === 'generating' ? 2000 : false,
  });
  const assetStatus = assetQuery.data?.status;

  // Когда вариант доехал до completed — фиксируем done через PATCH (статусное продвижение).
  useEffect(() => {
    if (prepared.status === 'generating' && assetStatus === 'completed') {
      api
        .patch(`/api/studio/${session.session_id}/prepared-updates/${prepared.prepared_id}`, {
          status: 'done',
        })
        .then(() => onChanged())
        .catch((err: Error) => toast.error(`Не удалось зафиксировать готовность варианта: ${err.message}`));
    }
    if (prepared.status === 'generating' && assetStatus === 'failed') {
      toast.error(`Генерация варианта упала: ${assetQuery.data?.error || 'без описания'}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assetStatus, prepared.status]);

  const patchStatus = useMutation({
    mutationFn: (patch: { backend?: string; workflow?: string }) =>
      api
        .patch(`/api/studio/${session.session_id}/prepared-updates/${prepared.prepared_id}`, patch)
        .then(unwrapData<PreparedUpdateT>),
    onSuccess: () => onChanged(),
    onError: (err: Error) => toast.error(`Не удалось обновить задание: ${err.message}`),
  });

  const generate = useMutation({
    mutationFn: async () => {
      const job = await api
        .post('/api/studio/image-jobs', {
          chapter: session.chapter,
          scene_id: session.scene_id,
          prompt: prepared.new_prompt,
          preferred_backend: prepared.backend,
          title: `обновление ${prepared.shot_id}`,
          plan_id: `prep:${prepared.prepared_id}`,
          shot_id: prepared.shot_id,
          size: sizeForAspect((prepared.applied_rules as { aspect_ratio?: string })?.aspect_ratio),
        })
        .then(unwrapData<{ asset_id: string }>);
      await api.patch(`/api/studio/${session.session_id}/prepared-updates/${prepared.prepared_id}`, {
        status: 'generating',
        new_asset_id: job.asset_id,
      });
      return job.asset_id;
    },
    onSuccess: () => {
      toast.success('Задание запущено через штатный image-jobs — статус читается из ассета');
      queryClient.invalidateQueries({ queryKey: ['studio-prepared', session.session_id] });
      queryClient.invalidateQueries({ queryKey: ['studio-apply', session.session_id] });
    },
    onError: (err: Error) => toast.error(`Не удалось запустить генерацию: ${err.message}`),
  });

  const backendOptions = Object.entries(executors).map(([value, ex]) => ({
    value,
    label: ex.label,
  }));

  return (
    <LCard
      size="small"
      style={{ marginBottom: 10 }}
      title={
        <LSpace wrap>
          <span data-testid={`prepared-title-${prepared.prepared_id}`}>
            Задание {prepared.shot_id}
          </span>
          <LTag color={statusMeta.color as 'default'} style={{ fontSize: 11 }}>
            {statusMeta.label}
          </LTag>
          <LTag style={{ fontSize: 11 }}>{prepared.backend}</LTag>
        </LSpace>
      }
      extra={
        <LSpace wrap>
          {prepared.source_asset_id && (
            <a href={assetFileUrl(prepared.source_asset_id)} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>
              старый кадр
            </a>
          )}
          {prepared.new_asset_id && (
            <a href={assetFileUrl(prepared.new_asset_id)} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>
              новый вариант
            </a>
          )}
        </LSpace>
      }
    >
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
        {prepared.source_asset_id && (
          <div>
            <div style={{ fontSize: 11, color: '#999' }}>старый кадр</div>
            <img
              src={assetFileUrl(prepared.source_asset_id)}
              alt="старый кадр"
              style={{ width: 100, borderRadius: 6, border: '1px solid var(--card-border)' }}
            />
          </div>
        )}
        {prepared.new_asset_id && (
          <div>
            <div style={{ fontSize: 11, color: '#999' }}>
              новый вариант {assetStatus ? `(${assetStatus})` : ''}
            </div>
            <img
              src={assetFileUrl(prepared.new_asset_id)}
              alt="новый вариант"
              style={{ width: 100, borderRadius: 6, border: '1px solid var(--card-border)' }}
            />
          </div>
        )}
      </div>

      <PromptBox label="новый промпт задания" text={prepared.new_prompt} />

      {prepared.motion_prompt && (
        <div style={{ marginTop: 6 }}>
          <PromptBox label="промпт движения (относится к видео)" text={prepared.motion_prompt} />
        </div>
      )}

      <div style={{ fontSize: 11, color: '#666', marginTop: 6 }}>
        применённые правила: rev {(prepared.applied_rules as { revision?: number })?.revision ?? '—'} ·
        референсы: {prepared.reference_asset_ids.length ? prepared.reference_asset_ids.join(', ') : '—'}
        {source && (
          <>
            {' '}
            · причина устаревания старого кадра: {source.reasons.join('; ')}
          </>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginTop: 10 }}>
        <div>
          <div style={{ fontSize: 11, color: '#999', marginBottom: 2 }}>исполнитель (workflow: {prepared.workflow})</div>
          <LSelect
            value={prepared.backend}
            options={backendOptions}
            disabled={prepared.status !== 'prepared' || patchStatus.isPending}
            onChange={(v) => patchStatus.mutate({ backend: String(v), workflow: executors[String(v)]?.workflow })}
            style={{ minWidth: 260 }}
          />
        </div>
        <div style={{ fontSize: 11, color: '#999', maxWidth: 320 }}>
          {executor ? (
            <>
              <div>{executor.execution_label}</div>
              <div>почему выбран: {executor.why}</div>
              <div>требования: {executor.requirements}</div>
            </>
          ) : (
            'исполнитель не найден в справочнике'
          )}
        </div>
      </div>

      <LSpace wrap style={{ marginTop: 10 }}>
        {prepared.status === 'prepared' && (
          <span data-testid={`generate-${prepared.prepared_id}`}>
            <LButton
              size="small"
              type="primary"
              disabled={generate.isPending}
              loading={generate.isPending}
              onClick={() => generate.mutate()}
            >
              {prepared.backend === 'mock' ? 'Сгенерировать mock-вариант' : 'Сгенерировать вариант'}
            </LButton>
          </span>
        )}
        {prepared.status === 'generating' && <LTag color="processing">генерация… (статус ассета)</LTag>}
        {(prepared.status === 'done' || prepared.status === 'approved') && (
          <span data-testid={`compare-${prepared.prepared_id}`}>
            <LButton size="small" onClick={onCompare}>
              Сравнить и утвердить
            </LButton>
          </span>
        )}
        <span style={{ fontSize: 11, color: '#999' }}>
          Запуск идёт штатным image-jobs (не вторым механизмом). Платные исполнители недоступны.
        </span>
      </LSpace>
    </LCard>
  );
}

// ── Сравнение старый ↔ новый + утверждение ──────────────────────

function CompareModal({
  prepared,
  source,
  sceneApprovedId,
  onClose,
  onApproved,
}: {
  prepared: PreparedUpdateT;
  source?: AffectedArtifactT;
  sceneApprovedId: string | null;
  onClose: () => void;
  onApproved: () => void;
}) {
  const [approving, setApproving] = useState(false);
  const isApprovedNow = !!prepared.new_asset_id && sceneApprovedId === prepared.new_asset_id;

  const approve = async () => {
    setApproving(true);
    try {
      await api.post(`/api/studio/${prepared.session_id}/prepared-updates/${prepared.prepared_id}/approve`);
      toast.success(`Новый кадр утверждён: план ${prepared.shot_id} · предыдущий кадр сохранён`);
      onApproved();
    } catch (err) {
      toast.error(`Не удалось утвердить кадр: ${(err as Error).message}`);
    } finally {
      setApproving(false);
    }
  };

  return (
    <LModal
      open
      title={`Сравнение кадров — план ${prepared.shot_id}`}
      onCancel={onClose}
      width={860}
      footer={
        <LSpace wrap>
          <LButton onClick={onClose}>Закрыть</LButton>
          <span data-testid="approve-new-frame">
            <LButton
              type="primary"
              disabled={approving || !prepared.new_asset_id || prepared.status === 'approved' || isApprovedNow}
              loading={approving}
              onClick={approve}
            >
              Утвердить новый кадр
            </LButton>
          </span>
        </LSpace>
      }
    >
      <div data-testid="compare-modal">
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 280px', minWidth: 240 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Старый кадр{' '}
              {source && (
                <LTag style={{ fontSize: 11 }}>
                  {FRAME_STATUS_META[source.frame_status || '']?.label || source.frame_status}
                </LTag>
              )}
            </div>
            {prepared.source_asset_id ? (
              <img
                src={assetFileUrl(prepared.source_asset_id)}
                alt="старый кадр"
                style={{ width: '100%', borderRadius: 8, border: '1px solid var(--card-border)' }}
              />
            ) : (
              <div style={{ color: '#999', fontSize: 12 }}>старого кадра не было</div>
            )}
            {source?.created_at && (
              <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>создан: {source.created_at}</div>
            )}
          </div>
          <div style={{ flex: '1 1 280px', minWidth: 240 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Новый кадр{' '}
              {isApprovedNow && <LTag color="success" style={{ fontSize: 11 }}>утверждён</LTag>}
              {prepared.status === 'approved' && !isApprovedNow && (
                <LTag color="success" style={{ fontSize: 11 }}>
                  утверждён ранее
                </LTag>
              )}
            </div>
            {prepared.new_asset_id ? (
              <img
                src={assetFileUrl(prepared.new_asset_id)}
                alt="новый кадр"
                style={{ width: '100%', borderRadius: 8, border: '1px solid var(--card-border)' }}
              />
            ) : (
              <div style={{ color: '#999', fontSize: 12 }}>вариант ещё не сгенерирован</div>
            )}
            {prepared.created_at && (
              <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>задание подготовлено: {prepared.created_at}</div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
          <PromptBox label="старый промпт" text={source?.prompt_used || ''} />
          <PromptBox label="новый промпт (итоговый по правилам)" text={prepared.new_prompt} />
        </div>

        <div style={{ fontSize: 11, color: '#666', marginTop: 10 }}>
          <div>
            какие правила изменились: {source?.reasons.join('; ') || '—'}
          </div>
          <div>
            ревизия правил на момент подготовки:{' '}
            {(prepared.applied_rules as { revision?: number })?.revision ?? '—'}
          </div>
          <div>
            референсы задания: {prepared.reference_asset_ids.join(', ') || '—'}
          </div>
          <div>
            утверждённый кадр сцены сейчас: {sceneApprovedId || '—'}
          </div>
        </div>

        <LAlert
          type="info"
          showIcon
          style={{ marginTop: 10 }}
          message="Утверждение не удаляет старый кадр"
          description="Новый вариант станет кадром плана и кадром-основой сцены. Прежнее утверждение сохраняется в истории версий; видео на старом кадре остаётся и помечается как требующее обновления."
        />
      </div>
    </LModal>
  );
}

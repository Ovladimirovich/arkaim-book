'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  LAlert,
  LButton,
  LEmpty,
  LModal,
  LSelect,
  LSpace,
  LSpin,
  LTag,
  toast,
} from '@/shared/ui/light';
import { DeleteOutlined } from '@ant-design/icons';
import { api } from '@/shared/lib/api';
import { AssetImage } from './asset-image';
import { AssetLightbox } from './asset-lightbox';
import {
  EXPERIMENT_STATUS_COLORS,
  EXPERIMENT_STATUS_LABELS,
  EXPERIMENT_STATUSES,
  unwrapData,
} from './types';
import type { ExperimentT, ExperimentsListT, StudioSessionT } from './types';

type Props = {
  session: StudioSessionT;
};

const AGE_OPTIONS = [
  { value: '', label: 'любой возраст' },
  { value: '1', label: 'старше 1 дня' },
  { value: '7', label: 'старше 7 дней' },
  { value: '30', label: 'старше 30 дней' },
];

const PAGE_SIZE = 20;

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function shotLabel(e: ExperimentT): string {
  const s = e.generation?.shot_id;
  return s || 'без шота';
}

function statusLabel(st?: string | null): string {
  return (st && EXPERIMENT_STATUS_LABELS[st as keyof typeof EXPERIMENT_STATUS_LABELS]) || st || '—';
}

export function ExperimentsPanel({ session }: Props) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<string>('');
  const [shotFilter, setShotFilter] = useState<string>('');
  const [backend, setBackend] = useState<string>('');
  const [age, setAge] = useState<string>('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [lightboxId, setLightboxId] = useState<string | null>(null);
  const [cleanupOpen, setCleanupOpen] = useState(false);

  const finalized =
    session.status === 'approved' || session.status === 'rejected' || session.status === 'sent';

  const params = useMemo(() => {
    const p = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (status) p.set('status', status);
    if (shotFilter) p.set('shot_id', shotFilter);
    if (backend) p.set('backend', backend);
    if (age) p.set('older_than_days', age);
    return p.toString();
  }, [status, shotFilter, backend, age, offset]);

  const listQuery = useQuery({
    queryKey: ['studio-experiments', session.session_id, params],
    queryFn: () =>
      api
        .get(`/api/studio/${session.session_id}/experiments?${params}`)
        .then(unwrapData<ExperimentsListT>),
    staleTime: 10_000,
  });

  const data = listQuery.data;
  const experiments = useMemo(() => data?.experiments || [], [data]);
  const groups = useMemo(() => data?.groups || [], [data]);
  const total = data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['studio-experiments', session.session_id] });
    queryClient.invalidateQueries({ queryKey: ['studio-affected'] });
    queryClient.invalidateQueries({ queryKey: ['studio-session', session.session_id] });
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const deleteBatch = useMutation({
    mutationFn: (ids: string[]) =>
      api
        .post(`/api/studio/${session.session_id}/experiments/delete-batch`, { asset_ids: ids })
        .then(unwrapData<{ deleted: string[]; deleted_count: number; protected: { asset_id: string; reason: string }[] }>),
    onSuccess: (res) => {
      toast.success(`Удалено: ${res.deleted_count}`);
      if (res.protected.length > 0) {
        toast.warning(
          `Не удалено (защищено): ${res.protected.map((p) => p.asset_id).join(', ')}`,
        );
      }
      setSelected(new Set());
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось удалить: ${err.message}`),
  });

  const archiveBatch = useMutation({
    mutationFn: (ids: string[]) =>
      api
        .post(`/api/studio/${session.session_id}/experiments/archive-batch`, { asset_ids: ids })
        .then(unwrapData<{ archived: string[]; protected: { asset_id: string; reason: string }[] }>),
    onSuccess: (res) => {
      toast.success(`Архивировано: ${res.archived.length}`);
      if (res.protected.length > 0) {
        toast.warning(`Не архивировано (защищено): ${res.protected.length}`);
      }
      setSelected(new Set());
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось архивировать: ${err.message}`),
  });

  const deleteOne = useMutation({
    mutationFn: (id: string) =>
      api.delete(`/api/studio/${session.session_id}/experiments/${id}`).then(unwrapData<{ deleted: string }>),
    onSuccess: () => {
      toast.success('Эксперимент удалён');
      setSelected(new Set());
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось удалить: ${err.message}`),
  });

  const cleanup = useMutation({
    mutationFn: (body: { older_than_days: number; dry_run: boolean }) =>
      api
        .post(`/api/studio/${session.session_id}/experiments/cleanup`, body)
        .then(unwrapData<{ would_delete: number; deleted: string[]; deleted_count: number; protected: { asset_id: string; reason: string }[] }>),
    onSuccess: (res) => {
      if (res.deleted_count !== undefined) {
        toast.success(`Удалено: ${res.deleted_count}`);
      }
      setCleanupOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось очистить: ${err.message}`),
  });

  const archiveCleanup = useMutation({
    mutationFn: (body: { older_than_days: number; dry_run: boolean }) =>
      api
        .post(`/api/studio/${session.session_id}/experiments/archive-cleanup`, body)
        .then(unwrapData<{ archived_count: number; archived: string[]; protected: { asset_id: string; reason: string }[]; dry_run: boolean }>),
    onSuccess: (res) => {
      toast.success(`Архивировано: ${res.archived_count}`);
      setCleanupOpen(false);
      invalidate();
    },
    onError: (err: Error) => toast.error(`Не удалось архивировать: ${err.message}`),
  });

  // Подсчёт по статусам — из текущего списка групп (без возрастного фильтра)
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const g of groups) {
      for (const [st, n] of Object.entries(g.by_status || {})) {
        c[st] = (c[st] || 0) + (n as number);
      }
    }
    return c;
  }, [groups]);

  const allShotIds = useMemo(() => {
    const ids = new Set<string>();
    for (const g of groups) if (g.shot_id) ids.add(g.shot_id);
    for (const e of experiments) if (e.generation?.shot_id) ids.add(e.generation.shot_id);
    return Array.from(ids).sort();
  }, [groups, experiments]);

  const allBackends = useMemo(() => {
    const set = new Set<string>();
    for (const e of experiments) if (e.generation?.backend) set.add(e.generation.backend);
    return Array.from(set).sort();
  }, [experiments]);

  const lightboxAsset = useMemo(
    () => experiments.find((e) => e.asset_id === lightboxId) || null,
    [experiments, lightboxId],
  );

  const selectedCount = selected.size;

  return (
    <div data-testid="experiments-panel">
      {/* Счётчики-фильтры по статусам */}
      <LSpace wrap style={{ marginBottom: 10 }}>
        {EXPERIMENT_STATUSES.map((st) => (
          <LButton
            key={st}
            size="small"
            type={status === st ? 'primary' : 'default'}
            onClick={() => {
              setStatus((prev) => (prev === st ? '' : st));
              setOffset(0);
            }}
            data-testid={`exp-status-filter-${st}`}
          >
            {EXPERIMENT_STATUS_LABELS[st]}: {counts[st] ?? 0}
          </LButton>
        ))}
        {status && (
          <LButton size="small" onClick={() => { setStatus(''); setOffset(0); }}>
            сбросить фильтр
          </LButton>
        )}
      </LSpace>

      {/* Фильтры: шот / исполнитель / возраст */}
      <LSpace wrap style={{ marginBottom: 10 }}>
        <LSelect
          style={{ minWidth: 180 }}
          placeholder="Шот"
          value={shotFilter || undefined}
          onChange={(v) => { setShotFilter((v as string) || ''); setOffset(0); }}
          options={[
            { value: '', label: 'все шоты' },
            ...allShotIds.map((s) => ({ value: s, label: s })),
          ]}
        />
        <LSelect
          style={{ minWidth: 180 }}
          placeholder="Исполнитель"
          value={backend || undefined}
          onChange={(v) => { setBackend((v as string) || ''); setOffset(0); }}
          options={[
            { value: '', label: 'все исполнители' },
            ...allBackends.map((b) => ({ value: b, label: b })),
          ]}
        />
        <LSelect
          style={{ minWidth: 160 }}
          placeholder="Возраст"
          value={age || undefined}
          onChange={(v) => { setAge((v as string) || ''); setOffset(0); }}
          options={AGE_OPTIONS}
        />
        <span style={{ fontSize: 12, color: '#999' }}>
          всего: <strong data-testid="exp-total">{total}</strong>
        </span>
      </LSpace>

      {/* Массовые действия */}
      {selectedCount > 0 && (
        <LSpace wrap style={{ marginBottom: 10 }}>
          <span style={{ fontSize: 12 }}>выбрано: {selectedCount}</span>
          <LButton
            size="small"
            danger
            disabled={selectedCount === 0 || deleteBatch.isPending}
            loading={deleteBatch.isPending}
            onClick={() => deleteBatch.mutate(Array.from(selected))}
            data-testid="exp-delete-selected"
          >
            Удалить выбранные
          </LButton>
          <LButton
            size="small"
            disabled={selectedCount === 0 || archiveBatch.isPending}
            loading={archiveBatch.isPending}
            onClick={() => archiveBatch.mutate(Array.from(selected))}
            data-testid="exp-archive-selected"
          >
            Архивировать выбранные
          </LButton>
          <LButton
            size="small"
            disabled={selectedCount === 0}
            onClick={() => setSelected(new Set())}
          >
            Отменить выбор
          </LButton>
        </LSpace>
      )}

      {/* Очистка и архивация старых */}
      <LSpace wrap style={{ marginBottom: 10 }}>
        <LButton
          size="small"
          icon={<DeleteOutlined />}
          disabled={finalized}
          onClick={() => setCleanupOpen(true)}
          data-testid="exp-open-cleanup"
        >
          Очистить старые эксперименты…
        </LButton>
        <LButton
          size="small"
          disabled={finalized}
          onClick={() => {
            const days = Number(age) || 7;
            archiveCleanup.mutate({ older_than_days: days, dry_run: true });
          }}
          data-testid="exp-archive-cleanup-preview"
        >
          Архивировать старые…
        </LButton>
      </LSpace>

      {listQuery.isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}>
          <LSpin />
        </div>
      ) : experiments.length === 0 ? (
        <LEmpty description="Нет результатов по выбранным фильтрам." />
      ) : (
        <>
          {/* Группировка: список текущих карточек с подписью шота */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {experiments.map((e) => {
              const st = e.experiment_status;
              const color = EXPERIMENT_STATUS_COLORS[(st as keyof typeof EXPERIMENT_STATUS_COLORS) || 'experimental'] as 'default' | 'processing' | 'success' | 'warning';
              return (
                <div
                  key={e.asset_id}
                  data-testid={`exp-card-${e.asset_id}`}
                  style={{
                    display: 'flex',
                    gap: 10,
                    padding: 8,
                    border: '1px solid var(--input-border)',
                    borderRadius: 8,
                    background: 'var(--card-bg)',
                  }}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(e.asset_id)}
                    disabled={st === 'approved'}
                    onChange={() => toggleSelect(e.asset_id)}
                    style={{ alignSelf: 'center' }}
                    data-testid={`exp-check-${e.asset_id}`}
                  />
                  <div style={{ width: 110, flexShrink: 0 }}>
                    <AssetImage
                      asset={e}
                      height={70}
                      onOpen={setLightboxId ? () => setLightboxId(e.asset_id) : undefined}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                      <LTag color={color}>{statusLabel(st)}</LTag>
                      <LTag>{shotLabel(e)}</LTag>
                      {e.generation?.backend && <LTag>исп.: {e.generation.backend}</LTag>}
                      {e.generation?.art_direction_revision != null && (
                        <LTag color="purple">rev {e.generation.art_direction_revision}</LTag>
                      )}
                      <span style={{ fontSize: 11, color: '#999' }}>
                        {formatDate(e.created_at)}
                      </span>
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: '#999',
                        marginTop: 4,
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        whiteSpace: 'pre-wrap',
                      }}
                      title={e.prompt_used || ''}
                    >
                      {e.prompt_used || '— промпт не сохранён'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, justifyContent: 'center' }}>
                    <LButton
                      size="small"
                      type="link"
                      onClick={() => setLightboxId(e.asset_id)}
                      data-testid={`exp-open-${e.asset_id}`}
                    >
                      открыть
                    </LButton>
                    {st !== 'approved' && (
                      <LButton
                        size="small"
                        danger
                        type="link"
                        disabled={deleteOne.isPending}
                        onClick={() => deleteOne.mutate(e.asset_id)}
                        data-testid={`exp-delete-${e.asset_id}`}
                      >
                        удалить
                      </LButton>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Пагинация */}
          <LSpace wrap style={{ marginTop: 12, justifyContent: 'center' }}>
            <LButton
              size="small"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              ← назад
            </LButton>
            <span style={{ fontSize: 12, color: '#999' }}>
              страница <strong>{currentPage}</strong> из {pages}
            </span>
            <LButton
              size="small"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              data-testid="exp-next-page"
            >
              далее →
            </LButton>
          </LSpace>
        </>
      )}

      {/* Лайтбокс: полный просмотр с провенансом */}
      <AssetLightbox
        asset={lightboxAsset}
        open={!!lightboxAsset}
        onClose={() => setLightboxId(null)}
        approved={lightboxAsset?.experiment_status === 'approved'}
      />

      {/* Модал очистки/архивирования старых */}
      <LModal
        open={cleanupOpen}
        title="Очистка и архивирование"
        onCancel={() => setCleanupOpen(false)}
        width={560}
        footer={
          <LSpace>
            <LButton onClick={() => setCleanupOpen(false)}>Закрыть</LButton>
            <LButton
              loading={archiveCleanup.isPending}
              disabled={archiveCleanup.data?.archived_count === 0 && archiveCleanup.isSuccess && !archiveCleanup.data.dry_run}
              onClick={() => {
                const days = Number(age) || 7;
                archiveCleanup.mutate({ older_than_days: days, dry_run: false });
              }}
              data-testid="exp-archive-confirm"
            >
              Архивировать ({archiveCleanup.data?.archived_count ?? '…'})
            </LButton>
            <LButton
              danger
              loading={cleanup.isPending}
              disabled={cleanup.data?.would_delete === 0 && cleanup.isSuccess}
              onClick={() => {
                const days = Number(age) || 7;
                cleanup.mutate({ older_than_days: days, dry_run: false });
              }}
              data-testid="exp-cleanup-confirm"
            >
              Удалить ({cleanup.data?.would_delete ?? '…'})
            </LButton>
          </LSpace>
        }
      >
        <div>
          <LAlert
            type="warning"
            showIcon
            message="Автоматически ничего не удаляется"
            description="Очистка удаляет только экспериментальные результаты старше выбранного возраста. Утверждённые кадры, референсы и источники видео защищены."
          />
          <div style={{ marginTop: 12 }}>
            <LSelect
              style={{ width: '100%' }}
              placeholder="Возраст экспериментов"
              value={age || '7'}
              onChange={(v) => setAge((v as string) || '7')}
              options={AGE_OPTIONS.filter((o) => o.value)}
            />
          </div>
          <LSpace wrap style={{ marginTop: 12 }}>
            <LButton
              size="small"
              disabled={cleanup.isPending || archiveCleanup.isPending}
              onClick={() => {
                const days = Number(age) || 7;
                Promise.all([
                  cleanup.mutateAsync({ older_than_days: days, dry_run: true }),
                  archiveCleanup.mutateAsync({ older_than_days: days, dry_run: true }),
                ]).catch(() => {});
              }}
              data-testid="exp-cleanup-preview"
            >
              Предпросмотр
            </LButton>
            {(cleanup.isSuccess || archiveCleanup.isSuccess) && (
              <span style={{ fontSize: 12, color: '#999' }}>
                {cleanup.isSuccess && (
                  <>
                    удалено: <strong>{cleanup.data?.would_delete ?? cleanup.data?.deleted_count ?? 0}</strong>
                    {cleanup.data?.protected?.length > 0 && ` · защищено: ${cleanup.data.protected.length}`}
                  </>
                )}
                {archiveCleanup.isSuccess && cleanup.isSuccess && ' · '}
                {archiveCleanup.isSuccess && (
                  <>
                    архив: <strong>{archiveCleanup.data?.archived_count ?? 0}</strong>
                    {archiveCleanup.data?.protected?.length > 0 && ` · защищено: ${archiveCleanup.data.protected.length}`}
                  </>
                )}
              </span>
            )}
          </LSpace>
        </div>
      </LModal>
    </div>
  );
}

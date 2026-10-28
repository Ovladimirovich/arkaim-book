'use client';

import { useState } from 'react';
import {
  LCard, LButton, LSpace, LTag, LSelect, LModal, LTextArea, LInput,
  LSpin, LEmpty, LAlert, toast,
} from '@/shared/ui/light';
import { StateView } from '@/shared/ui/StateView';
import {
  CheckOutlined, CloseOutlined, UndoOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';

// ── Типы (зеркало бэкенда Q3) ──────────────────────────────

type CandidateStatus = 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED';

type Candidate = {
  candidate_id: string;
  topic: string;
  status: CandidateStatus;
  file: string;
  locator: string;
  preview: string;
  source: string;
  model: string;
  generated_at: string;
  reviewed_by: string;
  reviewed_at: string;
  review_comment: string;
  file_blocked: boolean;
  requires_author_review: boolean;
  provenance_category: string;
};

type StatsData = {
  total: number;
  pending: number;
  by_status: Record<string, number>;
  by_file: Record<string, number>;
  by_source: Record<string, number>;
};

const STATUS_META: Record<CandidateStatus, { label: string; color: string }> = {
  PENDING_REVIEW: { label: 'На проверке', color: 'blue' },
  APPROVED: { label: 'Одобрено', color: 'green' },
  REJECTED: { label: 'Отклонено', color: 'red' },
};

const STATUS_OPTIONS = [
  { value: '', label: 'Все статусы' },
  { value: 'PENDING_REVIEW', label: 'На проверке' },
  { value: 'APPROVED', label: 'Одобрено' },
  { value: 'REJECTED', label: 'Отклонено' },
];

function formatDate(value: string | undefined | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('ru');
}

function errorText(error: unknown): string {
  if (error instanceof Error) return `Сервер ответил ошибкой: ${error.message}`;
  return 'Проверьте связь с сервером и повторите попытку.';
}

// ── Диалог решения: обязательный комментарий при APPROVE ───

type DecisionDialogState = {
  candidate: Candidate;
  action: 'approve' | 'reject' | 'reopen';
  comment: string;
  submitting: boolean;
} | null;

function DecisionDialog({
  state,
  onComment,
  onClose,
  onSubmit,
}: {
  state: DecisionDialogState;
  onComment: (comment: string) => void;
  onClose: () => void;
  onSubmit: (candidate: Candidate, action: 'approve' | 'reject' | 'reopen', comment: string) => void;
}) {
  if (!state) return null;

  const isApprove = state.action === 'approve';
  const title = isApprove
    ? 'Одобрить кандидата'
    : state.action === 'reject'
      ? 'Отклонить кандидата'
      : 'Вернуть в проверку';
  const buttonLabel = isApprove ? 'Одобрить' : state.action === 'reject' ? 'Отклонить' : 'Вернуть';

  return (
    <LModal
      open
      title={title}
      onCancel={onClose}
      footer={null}
    >
      <LSpace direction="vertical" style={{ width: '100%' }} size={12}>
        <div>
          <strong>{state.candidate.topic || state.candidate.locator}</strong>
        </div>
        <div style={{ fontSize: 13, color: 'var(--muted-foreground)' }}>
          {state.candidate.locator}
        </div>
        <LTextArea
          rows={3}
          autoSize={{ minRows: 3, maxRows: 6 }}
          placeholder="Комментарий (при одобрении — обязателен)"
          value={state.comment}
          onChange={(e) => onComment(e.target.value)}
        />
        {isApprove && (
          <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
            Одобрение делает запись доступной RAG и карточкам, но не превращает
            её в канон: provenance остаётся SYSTEM_INTERPRETATION.
          </div>
        )}
        <LSpace>
          <LButton
            data-testid="review-decision-submit"
            type={isApprove ? 'primary' : 'default'}
            danger={state.action === 'reject'}
            disabled={isApprove && state.comment.trim().length === 0}
            loading={state.submitting}
            onClick={() => onSubmit(state.candidate, state.action, state.comment)}
          >
            {buttonLabel}
          </LButton>
          <LButton data-testid="review-decision-cancel" onClick={onClose}>Отмена</LButton>
        </LSpace>
      </LSpace>
    </LModal>
  );
}

// ── Загрузка списка и статистики ───────────────────────────

async function fetchCandidates(params: { status?: string; q?: string }): Promise<{ candidates: Candidate[]; total: number }> {
  const search = new URLSearchParams();
  if (params.status) search.set('status', params.status);
  if (params.q) search.set('q', params.q);
  const query = search.toString();
  const resp = await api.get<{ ok: boolean; data: Candidate[]; total: number }>(
    `/api/candidates${query ? `?${query}` : ''}`,
  );
  return { candidates: resp.data || [], total: resp.total || 0 };
}

// ── Панель очереди ─────────────────────────────────────────

export function ReviewQueuePanel() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [dialog, setDialog] = useState<DecisionDialogState>(null);

  const candidatesQuery = useQuery({
    queryKey: ['review-queue', statusFilter, search],
    queryFn: () => fetchCandidates({ status: statusFilter || undefined, q: search || undefined }),
  });

  const statsQuery = useQuery({
    queryKey: ['review-queue-stats'],
    queryFn: () => api.get<{ ok: boolean; data: StatsData }>('/api/candidates/stats').then(r => r.data),
    staleTime: 30_000,
  });

  const decisionMutation = useMutation({
    mutationFn: async ({ candidate, action, comment }: { candidate: Candidate; action: string; comment: string }) => {
      const resp = await api.post<{ ok: boolean; data: Candidate }>(
        `/api/candidates/${candidate.candidate_id}/${action}`,
        { comment },
      );
      return resp.data;
    },
    onSuccess: (updated, variables) => {
      const verb =
        variables.action === 'approve' ? 'Одобрен' :
        variables.action === 'reject' ? 'Отклонён' : 'Возвращён в проверку';
      toast.success(`${verb}: ${variables.candidate.topic}`);
      setDialog(null);
      void queryClient.invalidateQueries({ queryKey: ['review-queue'] });
      void queryClient.invalidateQueries({ queryKey: ['review-queue-stats'] });
    },
    onError: (error) => {
      toast.error(`Решение не применено: ${errorText(error)}`);
    },
  });

  const handleSubmit = (candidate: Candidate, action: 'approve' | 'reject' | 'reopen', comment: string) => {
    if (action === 'approve' && comment.trim().length === 0) {
      toast.error('Укажите комментарий с обоснованием.');
      return;
    }
    decisionMutation.mutate({ candidate, action, comment });
  };

  const stats = statsQuery.data ?? null;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>Очередь проверки кандидатов</h2>
        {stats && (
          <LSpace size={8}>
            <LTag color="blue">На проверке: {stats.pending}</LTag>
            <LTag color="green">Одобрено: {stats.by_status.APPROVED ?? 0}</LTag>
            <LTag color="red">Отклонено: {stats.by_status.REJECTED ?? 0}</LTag>
          </LSpace>
        )}
      </div>

      <LAlert
        type="info"
        showIcon
        message="Одобрение делает запись доступной RAG, карточкам и при следующей сборке — миру. Одобренный кандидат остаётся системной интерпретацией (SYSTEM_INTERPRETATION) и не становится каноном книги."
        style={{ marginBottom: 12 }}
      />

      <LSpace style={{ marginBottom: 12 }} size={8}>
        <div style={{ width: 200 }}>
          <LSelect
            value={statusFilter}
            options={STATUS_OPTIONS}
            onChange={(v) => setStatusFilter(v ?? '')}
            placeholder="Статус"
            style={{ width: '100%' }}
          />
        </div>
        <div style={{ width: 240 }}>
          <LInputSearch value={search} onChange={setSearch} />
        </div>
        <LButton
          icon={<ReloadOutlined />}
          onClick={() => { void candidatesQuery.refetch(); void statsQuery.refetch(); }}
          loading={candidatesQuery.isFetching}
        >
          Обновить
        </LButton>
      </LSpace>

      {candidatesQuery.isError && (
        <StateView
          state="error"
          title="Не удалось загрузить очередь"
          description={errorText(candidatesQuery.error)}
          onRetry={() => void candidatesQuery.refetch()}
        />
      )}

      {candidatesQuery.isLoading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <LSpin size="large" />
        </div>
      )}

      {!candidatesQuery.isLoading && !candidatesQuery.isError && (candidatesQuery.data?.candidates.length ?? 0) === 0 && (
        <LEmpty description="В очереди нет кандидатов" />
      )}

      {!candidatesQuery.isLoading && !candidatesQuery.isError && (candidatesQuery.data?.candidates.length ?? 0) > 0 && (
        <div>
          {candidatesQuery.data!.candidates.map((item) => (
            <CandidateCard
              key={item.candidate_id}
              item={item}
              onDecision={(action) => setDialog({ candidate: item, action, comment: '', submitting: false })}
              busy={decisionMutation.isPending}
            />
          ))}
        </div>
      )}

      <DecisionDialog
        state={dialog}
        onComment={(comment) => setDialog((d) => d ? { ...d, comment } : d)}
        onClose={() => setDialog(null)}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

// ── Карточка кандидата ─────────────────────────────────────

function CandidateCard({
  item,
  onDecision,
  busy,
}: {
  item: Candidate;
  onDecision: (action: 'approve' | 'reject' | 'reopen') => void;
  busy: boolean;
}) {
  const meta = STATUS_META[item.status] ?? { label: item.status, color: 'default' };
  const canAct = item.status === 'PENDING_REVIEW';

  return (
    <LCard size="small" style={{ marginBottom: 8 }}>
      <LSpace direction="vertical" size={4} style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <strong>{item.topic || item.locator}</strong>
            <LTag color={meta.color as never}>{meta.label}</LTag>
            {item.file_blocked && <LTag color="orange">Файл целиком на проверке</LTag>}
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {canAct && (
              <>
                <LButton
                  type="primary"
                  size="small"
                  icon={<CheckOutlined />}
                  loading={busy}
                  onClick={() => onDecision('approve')}
                >
                  Одобрить
                </LButton>
                <LButton
                  size="small"
                  danger
                  icon={<CloseOutlined />}
                  loading={busy}
                  onClick={() => onDecision('reject')}
                >
                  Отклонить
                </LButton>
              </>
            )}
            {item.status === 'REJECTED' && (
              <LButton
                size="small"
                icon={<UndoOutlined />}
                loading={busy}
                onClick={() => onDecision('reopen')}
              >
                Вернуть
              </LButton>
            )}
          </div>
        </div>

        {item.preview && (
          <div style={{ fontSize: 13, color: 'var(--foreground)', lineHeight: 1.5 }}>{item.preview}</div>
        )}

        <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
          <LSpace size={12} wrap>
            <span>Источник: {item.source || '—'}</span>
            {item.model && <span>Модель: {item.model}</span>}
            <span>Создано: {formatDate(item.generated_at)}</span>
            <span>Provenance: {item.provenance_category || '—'}</span>
            <span>Файл: {item.file}</span>
          </LSpace>
        </div>

        {item.reviewed_by && (
          <div style={{ fontSize: 12, color: 'var(--muted-foreground)' }}>
            {item.status === 'APPROVED' && 'Одобрено'}
            {item.status === 'REJECTED' && 'Отклонено'}
            {' '}
            {item.reviewed_by} · {formatDate(item.reviewed_at)}
            {item.review_comment && ` — ${item.review_comment}`}
          </div>
        )}
      </LSpace>
    </LCard>
  );
}

// ── Поле поиска ────────────────────────────────────────────

function LInputSearch({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <LInput
      placeholder="Поиск по теме или тексту…"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      allowClear
    />
  );
}

/**
 * /temporal/queue — «Temporal-очередь» (F3_SPEC §2; editor+; M10.2).
 *
 * Контракты (live-факт F3-шаг 0):
 *   POST /book/temporal/pending-updates/scan    → {book_changed, new_findings, ...}
 *   GET  /book/temporal/pending-updates         → {data: finding[], total}
 *   GET  /book/temporal/pending-updates/stats   → {pending, confirmed, rejected}
 *   GET  /book/temporal/pending-updates/history → {confirmed[], rejected[]}
 *   POST /book/temporal/pending-updates/{id}/confirm → {finding_id, applied, manager}
 *   POST /book/temporal/pending-updates/{id}/reject  → {finding_id, applied, manager}
 *
 * M10.2-инварианты (красная линия R2): только серверные статусы; подтверждение —
 * серверный gate, никакого локального «принять». Reader-роль сюда не попадает
 * (RBAC-гейт навигации; список — reader+, confirm/reject/scan — editor+).
 * In-memory природа очереди: после перезапуска backend история пуста (O2-факт).
 */
'use client';

import { App, Button, Card, Col, Input, List, Popconfirm, Row, Space, Statistic, Tabs, Tag, Typography } from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  ApiError,
  confirmFinding,
  getQueueHistory,
  getQueueStats,
  listPending,
  rejectFinding,
  scanBook,
  type TemporalFinding,
} from '@/shared/api';
import { ProvenanceBadge } from '@/shared/ui/ProvenanceBadge';
import { RoleGate } from '@/shared/rbac/RoleGate';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;

/** F3: URL-гейт — навигация скрывает пункт, но прямой заход reader'а должен
 * получать явный отказ (F1-паттерн no-access), а не панель с 403-ами. */
const noAccess = (
  <Paragraph type="secondary">
    Temporal-очередь доступна редактору и администратору. Ваша роль не имеет прав на
    подтверждение временной модели мира.
  </Paragraph>
);

export default function TemporalQueuePage() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [rejectFor, setRejectFor] = useState<TemporalFinding | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // ── Список pending ──
  const pending = useQuery({
    queryKey: ['temporal', 'pending'],
    queryFn: () => listPending(),
    staleTime: 30_000,
  });

  // ── Счётчики ──
  const stats = useQuery({
    queryKey: ['temporal', 'stats'],
    queryFn: () => getQueueStats(),
    staleTime: 30_000,
  });

  // ── История confirmed/rejected ──
  const history = useQuery({
    queryKey: ['temporal', 'history'],
    queryFn: () => getQueueHistory(),
    staleTime: 30_000,
  });

  // ── Scan (M10: детектор → извлечение → pending) ──
  const scan = useMutation({
    mutationFn: () => scanBook(),
    onSuccess: (d) => {
      message.success(
        d.book_changed
          ? `Книга изменена: извлечено ${d.new_findings ?? 0} находок (${d.duplicate_findings ?? 0} дублей)`
          : 'Книга не менялась — новых предложений нет',
      );
      void qc.invalidateQueries({ queryKey: ['temporal', 'pending'] });
      void qc.invalidateQueries({ queryKey: ['temporal', 'stats'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Сканирование не удалось');
    },
  });

  // ── Confirm (серверный gate; editor+) ──
  const confirm = useMutation({
    mutationFn: (id: string) => confirmFinding(id),
    onSuccess: (d) => {
      message.success(`Находка подтверждена${d.applied ? ' и применена к модели мира' : ''}`);
      void qc.invalidateQueries({ queryKey: ['temporal'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось подтвердить');
    },
  });

  // ── Reject (editor+; reason ≤500) ──
  const reject = useMutation({
    mutationFn: (opts: { id: string; reason: string }) => rejectFinding(opts.id, opts.reason),
    onSuccess: () => {
      message.success('Находка отклонена');
      setRejectFor(null);
      setRejectReason('');
      void qc.invalidateQueries({ queryKey: ['temporal'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось отклонить');
    },
  });

  const findingCard = (f: TemporalFinding, status?: 'confirmed' | 'rejected') => (
    <List.Item
      key={f.id}
      actions={
        status
          ? [<Tag key="s" color={status === 'confirmed' ? 'green' : 'red'}>{status === 'confirmed' ? 'подтверждено' : 'отклонено'}</Tag>]
          : [
              <Popconfirm
                key="c"
                title="Подтвердить находку?"
                description="Находка будет применена к модели мира (серверный confirmation gate M10.2)."
                okText="Подтвердить"
                cancelText="Отмена"
                onConfirm={() => confirm.mutate(f.id)}
              >
                <Button type="primary" size="small" loading={confirm.isPending && confirm.variables === f.id}>
                  Подтвердить
                </Button>
              </Popconfirm>,
              <Button key="r" size="small" danger onClick={() => setRejectFor(f)}>
                Отклонить
              </Button>,
            ]
      }
    >
      <List.Item.Meta
        title={
          <Space wrap>
            <Text strong>{f.raw_text}</Text>
            <ProvenanceBadge category={f.category} confidence={f.confidence} />
            <Tag>стр. {f.line_number}</Tag>
            <Tag color="blue">{f.kind}</Tag>
          </Space>
        }
        description={
          <Space direction="vertical" size={2}>
            <Text type="secondary">{f.value}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {f.context}
            </Text>
            {status === 'rejected' && f.reason ? (
              <Text type="secondary" style={{ fontSize: 12 }}>
                Причина: {f.reason}
              </Text>
            ) : null}
          </Space>
        }
      />
    </List.Item>
  );

  return (
    <RoleGate roles={['editor', 'admin']} fallback={noAccess}>
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 900 }}>
      <Title level={3} style={{ margin: 0 }}>
        Temporal-очередь
      </Title>
      <Paragraph type="secondary">
        Предложения по временной модели мира: детектор находит изменения в книге, извлекает
        temporal-факты и предлагает их к подтверждению. Модель мира меняется только после
        подтверждения редактором.
      </Paragraph>

      {/* ── Счётчики + scan ── */}
      <Card>
        <Row gutter={[16, 16]} align="middle">
          <Col span={6}>
            <Statistic title="Ожидают" value={stats.data?.pending ?? '—'} loading={stats.isLoading} />
          </Col>
          <Col span={6}>
            <Statistic title="Подтверждено" value={stats.data?.confirmed ?? '—'} />
          </Col>
          <Col span={6}>
            <Statistic title="Отклонено" value={stats.data?.rejected ?? '—'} />
          </Col>
          <Col span={6}>
            <Button type="primary" loading={scan.isPending} onClick={() => scan.mutate()}>
              Сканировать книгу
            </Button>
          </Col>
        </Row>
      </Card>

      <Tabs
        items={[
          {
            key: 'pending',
            label: `Ожидают (${pending.data?.length ?? 0})`,
            children: (
              <StateView
                data={pending.data}
                loading={pending.isLoading}
                error={(pending.error as ApiError | null) ?? null}
                onRetry={() => void pending.refetch()}
                empty={(pending.data?.length ?? 0) === 0}
              >
                {(fs) => <List dataSource={fs} renderItem={(f) => findingCard(f)} />}
              </StateView>
            ),
          },
          {
            key: 'history',
            label: 'История',
            children: (
              <StateView
                data={history.data}
                loading={history.isLoading}
                error={(history.error as ApiError | null) ?? null}
                onRetry={() => void history.refetch()}
              >
                {(h) => (
                  <Space direction="vertical" size={16} style={{ width: '100%' }}>
                    {h.confirmed.length === 0 && h.rejected.length === 0 ? (
                      <Text type="secondary">
                        История пуста (очередь живёт в памяти backend — после перезапуска пусто).
                      </Text>
                    ) : (
                      <>
                        {h.confirmed.length > 0 && (
                          <List
                            header={<Text type="secondary">Подтверждённые</Text>}
                            dataSource={h.confirmed}
                            renderItem={(f) => findingCard(f, 'confirmed')}
                          />
                        )}
                        {h.rejected.length > 0 && (
                          <List
                            header={<Text type="secondary">Отклонённые</Text>}
                            dataSource={h.rejected}
                            renderItem={(f) => findingCard(f, 'rejected')}
                          />
                        )}
                      </>
                    )}
                  </Space>
                )}
              </StateView>
            ),
          },
        ]}
      />

      {/* ── Reject-диалог (reason ≤500, опционален) ── */}
      {rejectFor && (
        <Card size="small" title={`Отклонить: ${rejectFor.raw_text}`} style={{ marginTop: 8 }}>
          <Space.Compact style={{ width: '100%' }}>
            <Input
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value.slice(0, 500))}
              placeholder="Причина отклонения (необязательно, до 500 символов)"
              maxLength={500}
              onPressEnter={() => reject.mutate({ id: rejectFor.id, reason: rejectReason })}
            />
            <Button
              danger
              type="primary"
              loading={reject.isPending}
              onClick={() => reject.mutate({ id: rejectFor.id, reason: rejectReason })}
            >
              Отклонить
            </Button>
            <Button onClick={() => { setRejectFor(null); setRejectReason(''); }}>Отмена</Button>
          </Space.Compact>
        </Card>
      )}
    </div>
    </RoleGate>
  );
}

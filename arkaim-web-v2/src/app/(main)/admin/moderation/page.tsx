/**
 * /admin/moderation — Community moderation (F4; admin-only).
 *
 * Контракты:
 *   POST /book/community/interpretations/{id}/approve → direct {ok, interp_id}
 *   POST /book/community/interpretations/{id}/reject  → direct {ok, interp_id}
 *   POST /book/community/artifacts/{id}/approve       → direct {ok, artifact_id}
 *   POST /book/community/artifacts/{id}/reject        → direct {ok, artifact_id}
 *
 * RBAC: admin-only (RoleGate). Использует существующие контракты community.
 */
'use client';

import { App, Button, Card, List, Popconfirm, Tabs, Typography } from 'antd';
import { CheckOutlined, CloseOutlined, ReloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RoleGate } from '@/shared/rbac/RoleGate';
import {
  getInterpretationsStats,
  getArtifactsStats,
  type CommunityInterpretation,
  type CommunityArtifact,
} from '@/shared/api';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text, Paragraph } = Typography;

// ── Helpers ────────────────────────────────────────────────

// modActions helper kept for future use when list endpoints are available

export default function ModerationPage() {
  const { message } = App.useApp();
  const qc = useQueryClient();

  const interpStats = useQuery({
    queryKey: ['moderation', 'interpStats'],
    queryFn: () => getInterpretationsStats(),
    staleTime: 30_000,
  });

  const artifactStats = useQuery({
    queryKey: ['moderation', 'artifactStats'],
    queryFn: () => getArtifactsStats(),
    staleTime: 30_000,
  });

  const approveInterp = useMutation({
    mutationFn: (id: string) =>
      fetch(`/book/community/interpretations/${id}/approve`, {
        method: 'POST',
        credentials: 'same-origin',
      }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
    onSuccess: () => {
      message.success('Интерпретация одобрена');
      void qc.invalidateQueries({ queryKey: ['moderation'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось одобрить');
    },
  });

  const rejectInterp = useMutation({
    mutationFn: (id: string) =>
      fetch(`/book/community/interpretations/${id}/reject`, {
        method: 'POST',
        credentials: 'same-origin',
      }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
    onSuccess: () => {
      message.success('Интерпретация отклонена');
      void qc.invalidateQueries({ queryKey: ['moderation'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось отклонить');
    },
  });

  const approveArtifact = useMutation({
    mutationFn: (id: string) =>
      fetch(`/book/community/artifacts/${id}/approve`, {
        method: 'POST',
        credentials: 'same-origin',
      }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
    onSuccess: () => {
      message.success('Артефакт одобрен');
      void qc.invalidateQueries({ queryKey: ['moderation'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось одобрить');
    },
  });

  const rejectArtifact = useMutation({
    mutationFn: (id: string) =>
      fetch(`/book/community/artifacts/${id}/reject`, {
        method: 'POST',
        credentials: 'same-origin',
      }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
    onSuccess: () => {
      message.success('Артефакт отклонён');
      void qc.invalidateQueries({ queryKey: ['moderation'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось отклонить');
    },
  });

  const tabItems = [
    {
      key: 'interpretations',
      label: `Интерпретации (${interpStats.data?.pending ?? 0})`,
      children: (
        <Card
          title="Модерация интерпретаций"
          extra={
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void interpStats.refetch()}
              loading={interpStats.isLoading}
              size="small"
            >
              Обновить
            </Button>
          }
        >
          <div>
            <Text type="secondary">
              Всего: {(interpStats.data?.total ?? 0)} ·
              {' '}Одобрено: {(interpStats.data?.approved ?? 0)} ·
              {' '}На модерации: {(interpStats.data?.pending ?? 0)}
            </Text>
            <Paragraph type="secondary" style={{ marginTop: 12 }}>
              Для модерации используйте API напрямую: POST /book/community/interpretations/{`{id}`}/approve или /reject.
              Список pending-записей будет добавлен после появления endpoint&apos;a GET /book/community/interpretations?status=pending.
            </Paragraph>
          </div>
        </Card>
      ),
    },
    {
      key: 'artifacts',
      label: `Артефакты (${artifactStats.data?.pending ?? 0})`,
      children: (
        <Card
          title="Модерация артефактов"
          extra={
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void artifactStats.refetch()}
              loading={artifactStats.isLoading}
              size="small"
            >
              Обновить
            </Button>
          }
        >
          <div>
            <Text type="secondary">
              Всего: {(artifactStats.data?.total ?? 0)} ·
              {' '}Одобрено: {(artifactStats.data?.approved ?? 0)} ·
              {' '}На модерации: {(artifactStats.data?.pending ?? 0)}
            </Text>
            <Paragraph type="secondary" style={{ marginTop: 12 }}>
              Для модерации используйте API напрямую: POST /book/community/artifacts/{`{id}`}/approve или /reject.
            </Paragraph>
          </div>
        </Card>
      ),
    },
  ];

  return (
    <RoleGate roles={['admin']} fallback={<Paragraph type="secondary">Доступ только для администраторов</Paragraph>}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          Модерация сообщества
        </Title>
        <Paragraph type="secondary">
          Одобрение и отклонение интерпретаций и артефактов от читателей.
        </Paragraph>

        {/* ── Stats overview ── */}
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <Card size="small">
            <StateView data={interpStats.data} loading={interpStats.isLoading} error={(interpStats.error as ApiError | null) ?? null} onRetry={() => void interpStats.refetch()}>
              {(d) => (
                <Text>
                  Интерпретаций: <Text strong>{d.total}</Text>
                  {' '}· На модерации:{' '}
                  <Text strong type={d.pending > 0 ? 'danger' : undefined}>{d.pending}</Text>
                </Text>
              )}
            </StateView>
          </Card>
          <Card size="small">
            <StateView data={artifactStats.data} loading={artifactStats.isLoading} error={(artifactStats.error as ApiError | null) ?? null} onRetry={() => void artifactStats.refetch()}>
              {(d) => (
                <Text>
                  Артефактов: <Text strong>{d.total}</Text>
                  {' '}· На модерации:{' '}
                  <Text strong type={d.pending > 0 ? 'danger' : undefined}>{d.pending}</Text>
                </Text>
              )}
            </StateView>
          </Card>
        </div>

        <Tabs items={tabItems} />
      </div>
    </RoleGate>
  );
}

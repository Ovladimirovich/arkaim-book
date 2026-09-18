/**
 * /proposals/presence — Presence-очередь (F4; reader+ view, editor+ write).
 *
 * Контракты:
 *   GET  /book/presence/suggestions          → enveloped {ok, data: PresenceSuggestion[], total}
 *   GET  /book/presence/suggestions/stats    → enveloped {ok, data: {total, pending, approved, rejected}}
 *   POST /book/presence/suggestions/{id}/approve → direct {ok, suggestion_id}
 *   POST /book/presence/suggestions/{id}/reject  → direct {ok, suggestion_id}
 *   GET  /book/presence/trending             → enveloped {ok, data: TrendingItem[]}
 */
'use client';

import { App, Button, Card, Col, List, Popconfirm, Row, Statistic, Tag, Typography } from 'antd';
import { CheckOutlined, CloseOutlined, ReloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  approvePresence,
  getPresenceStats,
  getPresenceTrending,
  listPresenceSuggestions,
  rejectPresence,
  type PresenceSuggestion,
} from '@/shared/api';
import { ApiError } from '@/shared/api';
import { RoleGate } from '@/shared/rbac/RoleGate';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text, Paragraph } = Typography;

export default function PresencePage() {
  const { message } = App.useApp();
  const qc = useQueryClient();

  const suggestions = useQuery({
    queryKey: ['presence', 'list'],
    queryFn: () => listPresenceSuggestions(),
    staleTime: 30_000,
  });

  const stats = useQuery({
    queryKey: ['presence', 'stats'],
    queryFn: () => getPresenceStats(),
    staleTime: 30_000,
  });

  const trending = useQuery({
    queryKey: ['presence', 'trending'],
    queryFn: () => getPresenceTrending(),
    staleTime: 60_000,
  });

  const approve = useMutation({
    mutationFn: (id: string) => approvePresence(id),
    onSuccess: () => {
      message.success('Предложение принято');
      void qc.invalidateQueries({ queryKey: ['presence'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось принять');
    },
  });

  const reject = useMutation({
    mutationFn: (id: string) => rejectPresence(id),
    onSuccess: () => {
      message.success('Предложение отклонено');
      void qc.invalidateQueries({ queryKey: ['presence'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось отклонить');
    },
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        Presence-очередь
      </Title>
      <Paragraph type="secondary">
        Предложения от системы наблюдения за читательской активностью. Редактор может принять или отклонить.
      </Paragraph>

      {/* ── Stats ── */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8}>
          <Card>
            <StateView data={stats.data} loading={stats.isLoading} error={(stats.error as ApiError | null) ?? null} onRetry={() => void stats.refetch()}>
              {(d) => (
                <Statistic title="Всего" value={d.total} />
              )}
            </StateView>
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card>
            <StateView data={stats.data} loading={stats.isLoading} error={(stats.error as ApiError | null) ?? null} onRetry={() => void stats.refetch()}>
              {(d) => (
                <Statistic
                  title="Ожидают"
                  value={d.pending}
                  suffix={d.pending > 0 ? <Tag color="orange">{d.pending} на рассмотрении</Tag> : undefined}
                />
              )}
            </StateView>
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic title="Принято" value={stats.data?.approved ?? 0} suffix={<Tag color="green">одобрено</Tag>} />
          </Card>
        </Col>
      </Row>

      {/* ── Suggestions ── */}
      <Card
        title="Предложения"
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void suggestions.refetch()}
            loading={suggestions.isLoading}
          >
            Обновить
          </Button>
        }
      >
        <StateView
          data={suggestions.data}
          loading={suggestions.isLoading}
          error={(suggestions.error as ApiError | null) ?? null}
          onRetry={() => void suggestions.refetch()}
          empty={suggestions.data?.length === 0}
        >
          {(items) => (
            <List
              dataSource={items}
              renderItem={(item: PresenceSuggestion) => (
                <List.Item
                  actions={
                    item.status === 'pending'
                      ? [
                          <Popconfirm
                            key="approve"
                            title="Принять предложение?"
                            okText="Принять"
                            cancelText="Отмена"
                            onConfirm={() => void approve.mutateAsync(item.id)}
                          >
                            <Button size="small" type="primary" icon={<CheckOutlined />} shape="circle" />
                          </Popconfirm>,
                          <Popconfirm
                            key="reject"
                            title="Отклонить предложение?"
                            okText="Отклонить"
                            cancelText="Отмена"
                            onConfirm={() => void reject.mutateAsync(item.id)}
                          >
                            <Button size="small" danger icon={<CloseOutlined />} shape="circle" />
                          </Popconfirm>,
                        ]
                      : [<Tag key="s" color={item.status}>{item.status}</Tag>]
                  }
                >
                  <List.Item.Meta
                    title={<Text strong>{item.topic}</Text>}
                    description={
                      <>
                        <div>{item.content?.slice(0, 200)}</div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          источник: {item.source} · {new Date(item.created_at).toLocaleDateString('ru-RU')}
                        </Text>
                      </>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </StateView>
      </Card>

      {/* ── Trending ── */}
      <Card title="Тренды" size="small">
        <StateView
          data={trending.data}
          loading={trending.isLoading}
          error={(trending.error as ApiError | null) ?? null}
          onRetry={() => void trending.refetch()}
          empty={trending.data?.length === 0}
        >
          {(items) => (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {items.map((t) => (
                <Tag key={t.topic} color="blue" style={{ fontSize: 13 }}>
                  {t.topic} ({t.count})
                </Tag>
              ))}
            </div>
          )}
        </StateView>
      </Card>
    </div>
  );
}

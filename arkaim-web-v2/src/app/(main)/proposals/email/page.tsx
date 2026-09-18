/**
 * /proposals/email — Email-рассылка (F4; reader+ view, editor+ write).
 *
 * Контракты:
 *   GET  /book/email/drafts            → enveloped {ok, data: EmailDraft[]}
 *   POST /book/email/draft/{id}/send   → direct {ok, draft_id}
 *   GET  /book/email/stats             → enveloped {ok, data: {sent, pending, subscribers}}
 */
'use client';

import { App, Button, Card, Col, List, Popconfirm, Row, Statistic, Tag, Typography } from 'antd';
import { MailOutlined, ReloadOutlined, SendOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import {
  getEmailStats,
  listEmailDrafts,
  sendEmailDraft,
  type EmailDraft,
} from '@/shared/api';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text, Paragraph } = Typography;

export default function EmailPage() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const drafts = useQuery({
    queryKey: ['email', 'drafts'],
    queryFn: () => listEmailDrafts(),
    staleTime: 30_000,
  });

  const stats = useQuery({
    queryKey: ['email', 'stats'],
    queryFn: () => getEmailStats(),
    staleTime: 60_000,
  });

  const send = useMutation({
    mutationFn: (id: string) => sendEmailDraft(id),
    onSuccess: () => {
      message.success('Email отправлен');
      void qc.invalidateQueries({ queryKey: ['email'] });
      setSelectedId(null);
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось отправить');
    },
  });

  const selected = drafts.data?.find((d) => d.id === selectedId) ?? null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        Email-рассылка
      </Title>
      <Paragraph type="secondary">
        Управление email-черновиками и отправка подписчикам.
      </Paragraph>

      {/* ── Stats ── */}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic
              title="Отправлено"
              value={stats.data?.sent ?? 0}
              prefix={<MailOutlined />}
              suffix={<Tag color="green">всего</Tag>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic
              title="Подписчиков"
              value={stats.data?.subscribers ?? 0}
              suffix={<Tag color="blue">active</Tag>}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic
              title="Черновиков"
              value={drafts.data?.length ?? 0}
              suffix={<Tag color="orange">pending</Tag>}
            />
          </Card>
        </Col>
      </Row>

      {/* ── Drafts list + detail ── */}
      <Row gutter={[16, 16]}>
        <Col span={10}>
          <Card
            title="Черновики"
            extra={
              <Button
                icon={<ReloadOutlined />}
                onClick={() => void drafts.refetch()}
                loading={drafts.isLoading}
                size="small"
              >
                Обновить
              </Button>
            }
          >
            <StateView
              data={drafts.data}
              loading={drafts.isLoading}
              error={(drafts.error as ApiError | null) ?? null}
              onRetry={() => void drafts.refetch()}
              empty={drafts.data?.length === 0}
            >
              {(items) => (
                <List
                  dataSource={items}
                  renderItem={(item: EmailDraft) => (
                    <List.Item
                      style={{
                        cursor: 'pointer',
                        background: selectedId === item.id ? '#e6f4ff' : 'transparent',
                        border: selectedId === item.id ? '1px solid #1890ff' : '1px solid transparent',
                        borderRadius: 4,
                      }}
                      onClick={() => setSelectedId(item.id)}
                      actions={[
                        item.status === 'draft' ? (
                          <Tag key="st" color="orange">draft</Tag>
                        ) : (
                          <Tag key="st" color="green">sent</Tag>
                        ),
                      ]}
                    >
                      <List.Item.Meta
                        title={<Text ellipsis style={{ maxWidth: 180 }}>{item.subject}</Text>}
                        description={<Text type="secondary" style={{ fontSize: 12 }}>{item.topic}</Text>}
                      />
                    </List.Item>
                  )}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col span={14}>
          <Card
            title={selected ? `Черновик: ${selected.subject}` : 'Выберите черновик'}
            extra={
              selected?.status === 'draft' ? (
                <Popconfirm
                  title="Отправить email?"
                  description={`Отправить "${selected.subject}" всем подписчикам?`}
                  okText="Отправить"
                  cancelText="Отмена"
                  onConfirm={() => selectedId && void send.mutateAsync(selectedId)}
                  // loading={send.isPending} — Popconfirm не поддерживает loading в antd 5
                >
                  <Button type="primary" icon={<SendOutlined />} disabled={!selectedId || send.isPending}>
                    Отправить
                  </Button>
                </Popconfirm>
              ) : undefined
            }
          >
            {selected ? (
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>Тема: </Text>
                <Text strong>{selected.topic}</Text>
                <div style={{ marginTop: 12, padding: 12, background: '#fafafa', borderRadius: 4 }}>
                  <pre style={{ fontSize: 13, whiteSpace: 'pre-wrap', margin: 0 }}>
                    {selected.body?.slice(0, 500)}
                    {selected.body?.length > 500 ? '...' : ''}
                  </pre>
                </div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Создан: {new Date(selected.created_at).toLocaleString('ru-RU')}
                </Text>
              </div>
            ) : (
              <Paragraph type="secondary">Выберите черновик из списка слева</Paragraph>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

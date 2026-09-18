/**
 * /proposals/drafts — Approval черновиков контента (F4; reader+ view, editor+ write).
 *
 * Контракты:
 *   GET  /book/drafts                     → enveloped {ok, data: Draft[]}
 *   POST /book/drafts/{draft_id}/approve  → direct {ok, status: 'approved', draft_id}
 */
'use client';

import { App, Button, Card, List, Popconfirm, Typography } from 'antd';
import { CheckOutlined, ReloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { approveDraft, listDrafts, type Draft } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text, Paragraph } = Typography;

export default function DraftsPage() {
  const { message } = App.useApp();
  const qc = useQueryClient();

  const drafts = useQuery({
    queryKey: ['drafts', 'list'],
    queryFn: () => listDrafts('pending'),
    staleTime: 30_000,
  });

  const approve = useMutation({
    mutationFn: (id: string) => approveDraft(id),
    onSuccess: () => {
      message.success('Черновик одобрен');
      void qc.invalidateQueries({ queryKey: ['drafts'] });
    },
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось одобрить');
    },
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        Черновики контента
      </Title>
      <Paragraph type="secondary">
        Одобренные черновики переходят в публикуемое состояние. Требует роли editor+.
      </Paragraph>

      <Card
        title={`Черновики на рассмотрении (${drafts.data?.length ?? 0})`}
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void drafts.refetch()}
            loading={drafts.isLoading}
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
              renderItem={(item: Draft) => (
                <List.Item
                  actions={[
                    item.status === 'pending' ? (
                      <Popconfirm
                        key="approve"
                        title={`Одобрить "${item.topic}"?`}
                        description="Черновик будет переведён в статус опубликованного."
                        okText="Одобрить"
                        cancelText="Отмена"
                        onConfirm={() => void approve.mutateAsync(item.id)}
                      >
                        <Button
                          type="primary"
                          size="small"
                          icon={<CheckOutlined />}
                          loading={approve.isPending}
                        >
                          Одобрить
                        </Button>
                      </Popconfirm>
                    ) : (
                      <Text type="secondary" key="st">одобрено</Text>
                    ),
                  ]}
                >
                  <List.Item.Meta
                    title={<Text strong>{item.topic}</Text>}
                    description={
                      <>
                        <div>{item.content?.slice(0, 160)}</div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          тип: {item.type} · {new Date(item.created_at).toLocaleDateString('ru-RU')}
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
    </div>
  );
}

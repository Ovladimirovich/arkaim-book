'use client';

import { useState } from 'react';
import { Badge, Popover, List, Button, Typography, Space, Empty, Spin } from 'antd';
import { BellOutlined, CheckOutlined, DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { useRouter } from 'next/navigation';

const { Text } = Typography;

type Notification = {
  id: string;
  type: string;
  title: string;
  message: string;
  link: string;
  read: boolean;
  created_at: string;
};

const TYPE_LABELS: Record<string, { color: string }> = {
  comment_liked: { color: '#16a34a' },
  comment_added: { color: '#2563eb' },
  interpretation_approved: { color: '#16a34a' },
  interpretation_rejected: { color: '#dc2626' },
  artifact_approved: { color: '#16a34a' },
  artifact_rejected: { color: '#dc2626' },
  artifact_liked: { color: '#16a34a' },
  question_answered: { color: '#7c3aed' },
  system: { color: '#6b7280' },
};

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const router = useRouter();

  const { data, isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => api.get<{ notifications: Notification[]; unread_count: number }>('/book/community/notifications?limit=20'),
    refetchInterval: 300000, // Poll every 5min (was 30s — caused slowdowns)
    staleTime: 300000, // Cache for 5min
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/notifications/${id}/read`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => api.post('/book/community/notifications/read-all'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const notifications = data?.notifications || [];
  const unreadCount = data?.unread_count || 0;

  const content = (
    <div style={{ width: 320, maxHeight: 400, overflow: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, padding: '0 4px' }}>
        <Text strong>Уведомления</Text>
        {unreadCount > 0 && (
          <Button
            size="small"
            type="link"
            icon={<CheckOutlined />}
            onClick={() => markAllReadMutation.mutate()}
            loading={markAllReadMutation.isPending}
          >
            Прочитать все
          </Button>
        )}
      </div>

      {isLoading ? (
        <Spin style={{ display: 'block', textAlign: 'center', padding: 20 }} />
      ) : notifications.length === 0 ? (
        <Empty description="Нет уведомлений" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          size="small"
          dataSource={notifications}
          renderItem={(item: Notification) => {
            const meta = TYPE_LABELS[item.type] || { color: '#6b7280' };
            return (
              <List.Item
                style={{
                  padding: '8px 4px',
                  cursor: 'pointer',
                  backgroundColor: item.read ? undefined : '#f6f8ff',
                  borderRadius: 4,
                }}
                onClick={() => {
                  if (!item.read) markReadMutation.mutate(item.id);
                  if (item.link) {
                    router.push(item.link);
                    setOpen(false);
                  }
                }}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Badge color={meta.color} />
                      <Text style={{ fontSize: 13 }}>{item.title}</Text>
                    </Space>
                  }
                  description={
                    <div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{item.message}</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {new Date(item.created_at).toLocaleString('ru')}
                      </Text>
                    </div>
                  }
                />
              </List.Item>
            );
          }}
        />
      )}
    </div>
  );

  return (
    <Popover
      content={content}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="bottomRight"
    >
      <Badge count={unreadCount} size="small">
        <Button
          type="text"
          icon={<BellOutlined style={{ fontSize: 18 }} />}
          style={{ color: 'inherit' }}
        />
      </Badge>
    </Popover>
  );
}

'use client';

import { Card, Space, Typography, Progress, Spin } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';

const { Text } = Typography;

type QueueStats = {
  queue_size: number;
  workers_running: number;
  results_count: number;
  running: number;
};

export function GenerationQueueStatus({ compact = false }: { compact?: boolean }) {
  const { data, isLoading } = useQuery({
    queryKey: ['queue-status'],
    queryFn: () => api.get<QueueStats>('/book/assets/queue/status'),
    refetchInterval: 3000,
  });

  const stats = (data as { data?: QueueStats })?.data;

  if (isLoading) {
    return <Spin size="small" />;
  }

  if (!stats) {
    return null;
  }

  const { queue_size, workers_running, running, results_count } = stats;
  const total = queue_size + running + results_count || 1;
  const completed = results_count;

  if (total <= 1 && running === 0 && queue_size === 0) {
    return null;
  }

  if (compact) {
    return (
      <Space size={4}>
        {running > 0 && <LoadingOutlined style={{ color: '#1677ff' }} />}
        <Text style={{ fontSize: 12, color: '#999' }}>
          {running > 0 ? `${running} генерируется` : ''}
          {queue_size > 0 ? `, ${queue_size} в очереди` : ''}
        </Text>
      </Space>
    );
  }

  return (
    <Card size="small" title="Очередь генерации">
      <Space direction="vertical" style={{ width: '100%' }} size="small">
        <Progress
          percent={Math.round((completed / total) * 100)}
          format={() => `${completed}/${total}`}
          size="small"
        />
        <Space wrap>
          <Text type="secondary"><ClockCircleOutlined /> Очередь: {queue_size}</Text>
          <Text type="warning"><LoadingOutlined /> Генерируется: {running}</Text>
          <Text type="success"><CheckCircleOutlined /> Готово: {results_count}</Text>
        </Space>
      </Space>
    </Card>
  );
}

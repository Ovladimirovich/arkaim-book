'use client';

import { useState } from 'react';
import { Card, Typography, List, Button, Space, Tag, Tabs, Empty, message, Popconfirm, Spin } from 'antd';
import { CheckOutlined, CloseOutlined, DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';

const { Text, Paragraph } = Typography;

type Interpretation = {
  id: string;
  reader_name: string;
  text: string;
  themes: string[];
  characters: string[];
  created_at: string;
  status: string;
  likes: number;
};

type Artifact = {
  id: string;
  reader_name: string;
  title: string;
  description: string;
  category: string;
  source: string;
  connection_to_book: string;
  location: string;
  created_at: string;
  status: string;
  likes: number;
};

function InterpretationsModeration() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['admin-interpretations'],
    queryFn: () => api.get<{ interpretations: Interpretation[] }>('/book/community/interpretations?status=pending'),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/interpretations/${id}/approve`),
    onSuccess: () => {
      message.success('Интерпретация одобрена');
      queryClient.invalidateQueries({ queryKey: ['admin-interpretations'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/interpretations/${id}/reject`),
    onSuccess: () => {
      message.success('Интерпретация отклонена');
      queryClient.invalidateQueries({ queryKey: ['admin-interpretations'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/book/community/interpretations/${id}`),
    onSuccess: () => {
      message.success('Интерпретация удалена');
      queryClient.invalidateQueries({ queryKey: ['admin-interpretations'] });
    },
  });

  const items = data?.interpretations || [];

  if (isLoading) return <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>;

  if (items.length === 0) {
    return <Empty description="Нет интерпретаций на модерации" />;
  }

  return (
    <List
      dataSource={items}
      renderItem={(item: Interpretation) => (
        <Card size="small" style={{ marginBottom: 8 }}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Space>
              <Text strong>{item.reader_name || 'Читатель'}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>{new Date(item.created_at).toLocaleString('ru')}</Text>
            </Space>
            <Paragraph style={{ margin: 0 }}>{item.text}</Paragraph>
            <Space wrap>
              {item.themes.map((t, i) => <Tag key={i}>{t}</Tag>)}
              {item.characters.map((c, i) => <Tag key={i} color="blue">{c}</Tag>)}
            </Space>
            <Space>
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => approveMutation.mutate(item.id)}
                loading={approveMutation.isPending}
              >
                Одобрить
              </Button>
              <Button
                danger
                size="small"
                icon={<CloseOutlined />}
                onClick={() => rejectMutation.mutate(item.id)}
                loading={rejectMutation.isPending}
              >
                Отклонить
              </Button>
              <Popconfirm
                title="Удалить интерпретацию?"
                onConfirm={() => deleteMutation.mutate(item.id)}
              >
                <Button size="small" icon={<DeleteOutlined />} danger>
                  Удалить
                </Button>
              </Popconfirm>
            </Space>
          </Space>
        </Card>
      )}
    />
  );
}

function ArtifactsModeration() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['admin-artifacts'],
    queryFn: () => api.get<{ artifacts: Artifact[] }>('/book/community/artifacts?status=pending'),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/artifacts/${id}/approve`),
    onSuccess: () => {
      message.success('Артефакт одобрен');
      queryClient.invalidateQueries({ queryKey: ['admin-artifacts'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/artifacts/${id}/reject`),
    onSuccess: () => {
      message.success('Артефакт отклонён');
      queryClient.invalidateQueries({ queryKey: ['admin-artifacts'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/book/community/artifacts/${id}`),
    onSuccess: () => {
      message.success('Артефакт удалён');
      queryClient.invalidateQueries({ queryKey: ['admin-artifacts'] });
    },
  });

  const items = data?.artifacts || [];

  if (isLoading) return <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div>;

  if (items.length === 0) {
    return <Empty description="Нет артефактов на модерации" />;
  }

  return (
    <List
      dataSource={items}
      renderItem={(item: Artifact) => (
        <Card size="small" style={{ marginBottom: 8 }} title={item.title}>
          <Space direction="vertical" size={4} style={{ width: '100%' }}>
            <Space>
              <Tag color={item.category === 'archaeology' ? 'brown' : item.category === 'legend' ? 'purple' : 'blue'}>
                {item.category}
              </Tag>
              <Text strong>{item.reader_name || 'Читатель'}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>{new Date(item.created_at).toLocaleString('ru')}</Text>
            </Space>
            <Paragraph style={{ margin: 0 }}>{item.description}</Paragraph>
            <Paragraph type="secondary" style={{ margin: 0 }}>
              Источник: {item.source} | Связь: {item.connection_to_book}
            </Paragraph>
            {item.location && <Text type="secondary">Место: {item.location}</Text>}
            <Space>
              <Button
                type="primary"
                size="small"
                icon={<CheckOutlined />}
                onClick={() => approveMutation.mutate(item.id)}
                loading={approveMutation.isPending}
              >
                Одобрить
              </Button>
              <Button
                danger
                size="small"
                icon={<CloseOutlined />}
                onClick={() => rejectMutation.mutate(item.id)}
                loading={rejectMutation.isPending}
              >
                Отклонить
              </Button>
              <Popconfirm
                title="Удалить артефакт?"
                onConfirm={() => deleteMutation.mutate(item.id)}
              >
                <Button size="small" icon={<DeleteOutlined />} danger>
                  Удалить
                </Button>
              </Popconfirm>
            </Space>
          </Space>
        </Card>
      )}
    />
  );
}

export function ModerationPanel() {
  return (
    <Tabs
      items={[
        {
          key: 'interpretations',
          label: 'Интерпретации',
          children: <InterpretationsModeration />,
        },
        {
          key: 'artifacts',
          label: 'Артефакты',
          children: <ArtifactsModeration />,
        },
      ]}
    />
  );
}

'use client';

import { Table, Button, Popconfirm, message, Empty } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { StateView } from '@/shared/ui/StateView';

type Session = { id: string; user_id: string; expires_at: string; created_at: string };

// Честная индикация ошибок: единое описание для StateView (как на других экранах).
function errorDescription(error: unknown): string {
  return error instanceof Error
    ? `Сервер ответил ошибкой: ${error.message}.`
    : 'Проверьте связь с сервером и повторите попытку.';
}

export function SessionsPanel() {
  const queryClient = useQueryClient();

  const { data: sessions, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['admin-sessions'],
    queryFn: () => api.get<Session[]>('/auth/admin/sessions'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/admin/sessions/${id}`),
    onSuccess: () => { message.success('Сессия отозвана'); queryClient.invalidateQueries({ queryKey: ['admin-sessions'] }); },
    onError: () => message.error('Ошибка удаления сессии'),
  });

  // Честная индикация: при сбое — ошибка с повтором, а не пустая таблица.
  if (isError) return <StateView state="error" title="Не удалось загрузить сессии" description={errorDescription(error)} onRetry={() => void refetch()} />;

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', render: (v: string) => <code style={{ fontSize: 11 }}>{v.slice(0, 16)}...</code> },
    { title: 'Пользователь', dataIndex: 'user_id', key: 'user_id', render: (v: string) => v.slice(0, 8) + '...' },
    { title: 'Истекает', dataIndex: 'expires_at', key: 'expires_at', render: (v: string) => v ? new Date(v).toLocaleString('ru') : '—' },
    { title: 'Создана', dataIndex: 'created_at', key: 'created_at', render: (v: string) => v ? new Date(v).toLocaleString('ru') : '—' },
    {
      title: '', key: 'actions',
      render: (_: unknown, record: Session) => (
        <Popconfirm title="Отозвать сессию?" onConfirm={() => deleteMutation.mutate(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      {Array.isArray(sessions) && sessions.length === 0 ? (
        <Empty description="Нет активных сессий" />
      ) : (
        <Table columns={columns} dataSource={sessions || []} rowKey="id" loading={isLoading} size="small" />
      )}
    </>
  );
}

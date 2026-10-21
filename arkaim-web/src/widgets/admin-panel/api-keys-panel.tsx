'use client';

import { Table, Button, Tag, Popconfirm, message, Empty } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { StateView } from '@/shared/ui/StateView';

type ApiKey = { id: string; user_id: string; key_prefix: string; name?: string; last_used_at?: string; is_active: boolean; created_at: string };

// Честная индикация ошибок: единое описание для StateView (как на других экранах).
function errorDescription(error: unknown): string {
  return error instanceof Error
    ? `Сервер ответил ошибкой: ${error.message}.`
    : 'Проверьте связь с сервером и повторите попытку.';
}

export function ApiKeysPanel() {
  const queryClient = useQueryClient();

  const { data: keys, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['admin-api-keys'],
    queryFn: () => api.get<ApiKey[]>('/auth/admin/api-keys'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/admin/api-keys/${id}`),
    onSuccess: () => { message.success('API-ключ отозван'); queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] }); },
    onError: () => message.error('Ошибка удаления ключа'),
  });

  // Честная индикация: при сбое — ошибка с повтором, а не пустая таблица.
  if (isError) return <StateView state="error" title="Не удалось загрузить API-ключи" description={errorDescription(error)} onRetry={() => void refetch()} />;

  const columns = [
    { title: 'Префикс', dataIndex: 'key_prefix', key: 'prefix', render: (v: string) => <code>{v}...</code> },
    { title: 'Имя', dataIndex: 'name', key: 'name', render: (v: string) => v || '—' },
    { title: 'Пользователь', dataIndex: 'user_id', key: 'user_id', render: (v: string) => v.slice(0, 8) + '...' },
    { title: 'Последнее использование', dataIndex: 'last_used_at', key: 'last_used', render: (v: string) => v ? new Date(v).toLocaleString('ru') : 'Никогда' },
    { title: 'Статус', dataIndex: 'is_active', key: 'status', render: (v: boolean) => v ? <Tag color="green">Активен</Tag> : <Tag color="red">Отозван</Tag> },
    {
      title: '', key: 'actions',
      render: (_: unknown, record: ApiKey) => record.is_active ? (
        <Popconfirm title="Отозвать ключ?" onConfirm={() => deleteMutation.mutate(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ) : null,
    },
  ];

  return (
    <>
      {Array.isArray(keys) && keys.length === 0 ? (
        <Empty description="Нет API-ключей" />
      ) : (
        <Table columns={columns} dataSource={keys || []} rowKey="id" loading={isLoading} size="small" />
      )}
    </>
  );
}

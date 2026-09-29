'use client';

import { Table, Button, Tag, Popconfirm, message, Empty } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';

type ApiKey = { id: string; user_id: string; key_prefix: string; name?: string; last_used_at?: string; is_active: boolean; created_at: string };

export function ApiKeysPanel() {
  const queryClient = useQueryClient();

  const { data: keys, isLoading } = useQuery({
    queryKey: ['admin-api-keys'],
    queryFn: () => api.get<ApiKey[]>('/auth/admin/api-keys'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/admin/api-keys/${id}`),
    onSuccess: () => { message.success('API-ключ отозван'); queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] }); },
    onError: () => message.error('Ошибка удаления ключа'),
  });

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

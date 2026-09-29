'use client';

import { useState } from 'react';
import { Table, Button, Select, Tag, Space, Popconfirm, message, Drawer, Descriptions, Spin, Input, Row, Col, Statistic, Card } from 'antd';
import { DeleteOutlined, EyeOutlined, SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { User } from '@/shared/types';

export function UsersPanel() {
  const queryClient = useQueryClient();
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string | null>(null);

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get<User[]>('/auth/admin/users'),
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) =>
      api.post(`/auth/admin/users/${id}/role?role=${role}`),
    onSuccess: () => { message.success('Роль изменена'); queryClient.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: () => message.error('Ошибка выполнения'),
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => api.post(`/auth/admin/users/${id}/toggle`),
    onSuccess: () => { message.success('Статус изменён'); queryClient.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: () => message.error('Ошибка выполнения'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/admin/users/${id}`),
    onSuccess: () => { message.success('Пользователь удалён'); queryClient.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: () => message.error('Ошибка выполнения'),
  });

  const viewUser = async (id: string) => {
    try {
      const user = await api.get<User>(`/auth/admin/users/${id}`);
      setSelectedUser(user);
      setDrawerOpen(true);
    } catch {
      message.error('Ошибка загрузки пользователя');
    }
  };

  const exportUsers = () => {
    if (!users) return;
    const csv = ['ID,Имя,Провайдер,Роль,Статус,Создан']
      .concat(users.map(u => `${u.id},${u.display_name || u.username || ''},${u.provider},${u.role},${u.is_active ? 'Активен' : 'Заблокирован'},${u.created_at || ''}`))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'users.csv'; a.click();
    URL.revokeObjectURL(url);
    message.success('Файл скачан');
  };

  const filtered = (users || []).filter(u => {
    const matchSearch = !searchText || (u.display_name || u.username || u.id).toLowerCase().includes(searchText.toLowerCase());
    const matchRole = !roleFilter || u.role === roleFilter;
    return matchSearch && matchRole;
  });

  const roleCounts = (users || []).reduce((acc, u) => { acc[u.role] = (acc[u.role] || 0) + 1; return acc; }, {} as Record<string, number>);

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 100, render: (v: string) => <code style={{ fontSize: 12 }}>{v.slice(0, 8)}...</code> },
    { title: 'Имя', key: 'name', render: (_: unknown, r: User) => r.display_name || r.username || '—' },
    { title: 'Провайдер', dataIndex: 'provider', key: 'provider', render: (v: string) => <Tag>{v}</Tag> },
    {
      title: 'Роль', dataIndex: 'role', key: 'role',
      render: (role: string, record: User) => (
        <Select value={role} size="small" style={{ width: 100 }}
          onChange={(v) => roleMutation.mutate({ id: record.id, role: v })}
          options={[
            { value: 'reader', label: 'reader' },
            { value: 'editor', label: 'editor' },
            { value: 'admin', label: 'admin' },
          ]}
        />
      ),
    },
    {
      title: 'Статус', dataIndex: 'is_active', key: 'status',
      render: (v: boolean) => v ? <Tag color="green">Активен</Tag> : <Tag color="red">Заблокирован</Tag>,
    },
    {
      title: 'Действия', key: 'actions',
      render: (_: unknown, record: User) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => viewUser(record.id)} />
          <Button size="small" onClick={() => toggleMutation.mutate(record.id)}>
            {record.is_active ? 'Деакт.' : 'Акт.'}
          </Button>
          <Popconfirm title="Удалить пользователя?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      {/* Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="Всего" value={users?.length ?? 0} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="Читателей" value={roleCounts['reader'] ?? 0} valueStyle={{ color: '#16a34a' }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="Редакторов" value={roleCounts['editor'] ?? 0} valueStyle={{ color: '#2563eb' }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="Админов" value={roleCounts['admin'] ?? 0} valueStyle={{ color: '#dc2626' }} /></Card></Col>
      </Row>

      {/* Search & Filter */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Input
            placeholder="Поиск по имени или ID..."
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            allowClear
            style={{ width: 300 }}
          />
        </Col>
        <Col>
          <Select
            placeholder="Фильтр по роли"
            allowClear
            style={{ width: 150 }}
            value={roleFilter}
            onChange={setRoleFilter}
            options={[
              { value: 'reader', label: 'reader' },
              { value: 'editor', label: 'editor' },
              { value: 'admin', label: 'admin' },
            ]}
          />
        </Col>
        <Col>
          <Button icon={<DownloadOutlined />} onClick={exportUsers}>Экспорт CSV</Button>
        </Col>
      </Row>

      <Table
        columns={columns}
        dataSource={filtered}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20, showTotal: (total) => `Всего: ${total}` }}
      />

      <Drawer title="Детали пользователя" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={400}>
        {selectedUser ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{selectedUser.id}</Descriptions.Item>
            <Descriptions.Item label="Провайдер">{selectedUser.provider}</Descriptions.Item>
            <Descriptions.Item label="Имя">{selectedUser.username || '—'}</Descriptions.Item>
            <Descriptions.Item label="Отображаемое имя">{selectedUser.display_name || '—'}</Descriptions.Item>
            <Descriptions.Item label="Роль">{selectedUser.role}</Descriptions.Item>
            <Descriptions.Item label="Статус">{selectedUser.is_active ? 'Активен' : 'Заблокирован'}</Descriptions.Item>
            <Descriptions.Item label="Создан">{selectedUser.created_at || '—'}</Descriptions.Item>
          </Descriptions>
        ) : <Spin />}
      </Drawer>
    </>
  );
}

'use client';

import { useState } from 'react';
import { Table, Button, InputNumber, Select, Input, Space, Popconfirm, message, Form, Card, Empty } from 'antd';
import { PlusOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import type { Invite } from '@/shared/types';

export function InvitesPanel() {
  const queryClient = useQueryClient();
  const [formOpen, setFormOpen] = useState(false);
  const [form] = Form.useForm();

  const { data: invites, isLoading } = useQuery({
    queryKey: ['admin-invites'],
    queryFn: () => api.get<Invite[]>('/auth/admin/invites'),
  });

  const createMutation = useMutation({
    mutationFn: (values: { role: string; max_uses: number; note?: string }) => api.post<{ url: string }>(
      `/auth/admin/invites?role=${values.role}&max_uses=${values.max_uses}&note=${values.note || ''}`
    ),
    onSuccess: (data) => {
      navigator.clipboard.writeText(data.url);
      message.success('Инвайт создан, ссылка скопирована');
      queryClient.invalidateQueries({ queryKey: ['admin-invites'] });
      setFormOpen(false);
      form.resetFields();
    },
    onError: () => message.error('Ошибка'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/admin/invites/${id}`),
    onSuccess: () => { message.success('Инвайт удалён'); queryClient.invalidateQueries({ queryKey: ['admin-invites'] }); },
    onError: () => message.error('Ошибка'),
  });

  const copyUrl = (url: string) => {
    navigator.clipboard.writeText(url);
    message.info('Ссылка скопирована');
  };

  const columns = [
    {
      title: 'Ссылка', key: 'url', width: 300,
      render: (_: unknown, r: Invite) => (
        <Space>
          <code style={{ fontSize: 11 }}>{r.url?.slice(0, 40)}...</code>
          <Button size="small" icon={<CopyOutlined />} onClick={() => copyUrl(r.url)} />
        </Space>
      ),
    },
    { title: 'Роль', dataIndex: 'role', key: 'role', render: (v: string) => <span>{v}</span> },
    { title: 'Использовано', key: 'uses', render: (_: unknown, r: Invite) => `${r.use_count} / ${r.max_uses}` },
    { title: 'Заметка', dataIndex: 'note', key: 'note', render: (v: string) => v || '—' },
    {
      title: 'Статус', key: 'status',
      render: (_: unknown, r: Invite) => {
        const active = r.is_active && r.use_count < r.max_uses;
        return active ? <span style={{ color: '#16a34a' }}>Активен</span> : <span style={{ color: '#dc2626' }}>Использован</span>;
      },
    },
    {
      title: '', key: 'actions',
      render: (_: unknown, r: Invite) => (
        <Popconfirm title="Удалить инвайт?" onConfirm={() => deleteMutation.mutate(r.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormOpen(true)}>
          Создать инвайт
        </Button>
      </div>

      {formOpen && (
        <Card style={{ marginBottom: 16 }}>
          <Form form={form} layout="inline" onFinish={(v) => createMutation.mutate(v)}>
            <Form.Item name="role" initialValue="reader" label="Роль">
              <Select style={{ width: 120 }} options={[
                { value: 'reader', label: 'reader' },
                { value: 'editor', label: 'editor' },
              ]} />
            </Form.Item>
            <Form.Item name="max_uses" initialValue={1} label="Макс. использований">
              <InputNumber min={1} max={100} />
            </Form.Item>
            <Form.Item name="note" label="Заметка">
              <Input placeholder="Опционально" />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={createMutation.isPending}>Создать</Button>
                <Button onClick={() => setFormOpen(false)}>Отмена</Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>
      )}

      {Array.isArray(invites) && invites.length === 0 ? (
        <Empty description="Нет инвайтов" />
      ) : (
        <Table columns={columns} dataSource={invites || []} rowKey="id" loading={isLoading} size="small" />
      )}
    </>
  );
}

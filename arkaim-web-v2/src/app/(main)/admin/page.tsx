/**
 * /admin — админ-панель (admin-only).
 *
 * Использует только существующие backend endpoints без изменений:
 *   GET  /auth/admin/stats             — сводная статистика
 *   GET  /auth/admin/users             — список пользователей
 *   POST /auth/admin/users/{id}/role   — смена роли
 *   POST /auth/admin/users/{id}/toggle — активация/деактивация
 *   DELETE /auth/admin/users/{id}      — удаление пользователя
 *   GET  /auth/admin/api-keys          — список API-ключей
 *   DELETE /auth/admin/api-keys/{id}   — удаление ключа
 */
'use client';

import {
  App,
  Button,
  Card,
  Col,
  Popconfirm,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import { DeleteOutlined, ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RoleGate } from '@/shared/rbac/RoleGate';
import {
  getAdminStats,
  getAdminUsers,
  updateUserRole,
  toggleUser,
  deleteUser,
  getAdminApiKeys,
  deleteAdminApiKey,
  type AdminStats,
  type AdminUser,
  type AdminApiKey,
  type Role,
} from '@/shared/api';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text } = Typography;

const ROLES: { value: Role; label: string }[] = [
  { value: 'reader', label: 'reader' },
  { value: 'editor', label: 'editor' },
  { value: 'admin', label: 'admin' },
];

// ── No-access fallback ─────────────────────────────────────

const noAccess = (
  <div style={{ padding: 48, textAlign: 'center' }}>
    <Text type="secondary">Нет доступа. Нужна роль admin.</Text>
  </div>
);

// ── Helpers ────────────────────────────────────────────────

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  } catch {
    return iso;
  }
}

// ── Page ───────────────────────────────────────────────────

export default function AdminPage() {
  const { message: msgApi } = App.useApp();
  const qc = useQueryClient();

  const stats = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: getAdminStats,
    staleTime: 60_000,
  });

  const users = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: getAdminUsers,
    staleTime: 30_000,
  });

  const keys = useQuery({
    queryKey: ['admin', 'apiKeys'],
    queryFn: getAdminApiKeys,
    staleTime: 60_000,
  });

  // ── Mutations ────────────────────────────────────────────

  const roleMut = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) => updateUserRole(userId, role),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Ошибка смены роли';
      msgApi.error(msg);
    },
  });

  const toggleMut = useMutation({
    mutationFn: (id: string) => toggleUser(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Ошибка переключения';
      msgApi.error(msg);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['admin', 'users'] }),
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Ошибка удаления';
      msgApi.error(msg);
    },
  });

  const deleteKeyMut = useMutation({
    mutationFn: (id: string) => deleteAdminApiKey(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['admin', 'apiKeys'] }),
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Ошибка удаления ключа';
      msgApi.error(msg);
    },
  });

  // ── Render ───────────────────────────────────────────────

  return (
    <RoleGate roles={['admin']} fallback={noAccess}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        Администрирование
      </Title>

      {/* ── Stats overview ── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={stats.data}
              loading={stats.isLoading}
              error={(stats.error as ApiError | null) ?? null}
              onRetry={() => void stats.refetch()}
            >
              {(d: AdminStats) => (
                <Statistic
                  title="Всего пользователей"
                  value={d.users.total}
                  suffix={<Tag color="blue">reader: {d.users.by_role.reader ?? 0}</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={stats.data}
              loading={stats.isLoading}
              error={(stats.error as ApiError | null) ?? null}
              onRetry={() => void stats.refetch()}
            >
              {(d: AdminStats) => (
                <Statistic
                  title="Администраторов"
                  value={d.users.by_role.admin ?? 0}
                  suffix={<Tag color="gold">admin</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={stats.data}
              loading={stats.isLoading}
              error={(stats.error as ApiError | null) ?? null}
              onRetry={() => void stats.refetch()}
              empty={!stats.data?.presence}
            >
              {(d: AdminStats) => (
                <Statistic
                  title="Ожидают модерации"
                  value={d.presence.pending_suggestions}
                  suffix={<Tag color="orange">presence</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={stats.data}
              loading={stats.isLoading}
              error={(stats.error as ApiError | null) ?? null}
              onRetry={() => void stats.refetch()}
              empty={!stats.data?.email}
            >
              {(d: AdminStats) => (
                <Statistic
                  title="Черновиков email"
                  value={d.email.drafts}
                  suffix={<Tag color="purple">{d.email.subscribers} подп.</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>
      </Row>

      {/* ── Users table ── */}
      <Card
        title="Пользователи"
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void users.refetch()}
            disabled={users.isLoading}
          >
            Обновить
          </Button>
        }
      >
        <StateView
          data={users.data}
          loading={users.isLoading}
          error={(users.error as ApiError | null) ?? null}
          onRetry={() => void users.refetch()}
          empty={users.data?.length === 0}
        >
          {(data: AdminUser[]) => (
            <Table<AdminUser>
              dataSource={data}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 20, showSizeChanger: false }}
              columns={[
                {
                  title: 'Имя',
                  render: (_: unknown, r: AdminUser) => (
                    <div>
                      <div style={{ fontWeight: 500 }}>{r.display_name || r.username}</div>
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {r.username} · {r.provider}
                      </Text>
                    </div>
                  ),
                },
                {
                  title: 'Роль',
                  dataIndex: 'role',
                  render: (role: Role, record: AdminUser) => (
                    <Select
                      value={role}
                      size="small"
                      style={{ width: 100 }}
                      options={ROLES}
                      onChange={(v) => roleMut.mutate({ userId: record.id, role: v })}
                      loading={roleMut.isPending}
                      disabled={roleMut.isPending}
                    />
                  ),
                },
                {
                  title: 'Статус',
                  dataIndex: 'is_active',
                  render: (active: number) => (
                    <Tag color={active ? 'green' : 'default'}>
                      {active ? 'активен' : 'неактивен'}
                    </Tag>
                  ),
                },
                {
                  title: 'Создан',
                  dataIndex: 'created_at',
                  render: (v: string) => fmtDate(v),
                },
                {
                  title: '',
                  key: 'actions',
                  width: 100,
                  render: (_: unknown, record: AdminUser) => (
                    <Space size={4}>
                      <Popconfirm
                        title={record.is_active ? 'Деактивировать?' : 'Активировать?'}
                        description={`${record.display_name || record.username}?`}
                        okText={record.is_active ? 'Деактивировать' : 'Активировать'}
                        cancelText="Отмена"
                        okButtonProps={{ danger: !!record.is_active }}
                        onConfirm={() => toggleMut.mutate(record.id)}
                        disabled={toggleMut.isPending}
                      >
                        <Button
                          type="text"
                          size="small"
                          icon={<SyncOutlined spin={toggleMut.isPending} />}
                          disabled={toggleMut.isPending}
                        />
                      </Popconfirm>
                      <Popconfirm
                        title="Удалить пользователя"
                        description={`«${record.display_name || record.username}»? Это действие необратимо.`}
                        okText="Удалить"
                        cancelText="Отмена"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => deleteMut.mutate(record.id)}
                        disabled={deleteMut.isPending}
                      >
                        <Button
                          type="text"
                          danger
                          size="small"
                          icon={<DeleteOutlined />}
                          disabled={deleteMut.isPending}
                        />
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]}
            />
          )}
        </StateView>
      </Card>

      {/* ── API Keys ── */}
      <Card
        title="API-ключи"
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => void keys.refetch()}
            disabled={keys.isLoading}
          >
            Обновить
          </Button>
        }
      >
        <StateView
          data={keys.data}
          loading={keys.isLoading}
          error={(keys.error as ApiError | null) ?? null}
          onRetry={() => void keys.refetch()}
          empty={keys.data?.length === 0}
        >
          {(data: AdminApiKey[]) => (
            <Table<AdminApiKey>
              dataSource={data}
              rowKey="id"
              size="small"
              columns={[
                {
                  title: 'Префикс ключа',
                  dataIndex: 'key_prefix',
                  render: (v: string) => (
                    <Text code style={{ fontSize: 11 }}>{v}</Text>
                  ),
                },
                {
                  title: 'Имя',
                  dataIndex: 'name',
                  render: (v: string | null) => v ?? '—',
                },
                {
                  title: 'Последнее использование',
                  dataIndex: 'last_used_at',
                  render: (v: string | null) => v ? fmtDate(v) : 'никогда',
                },
                {
                  title: 'Создан',
                  dataIndex: 'created_at',
                  render: (v: string) => fmtDate(v),
                },
                {
                  title: '',
                  key: 'actions',
                  width: 60,
                  render: (_: unknown, record: AdminApiKey) => (
                    <Popconfirm
                      title="Удалить ключ"
                      description="Ключ будет безвозвратно удалён."
                      okText="Удалить"
                      cancelText="Отмена"
                      okButtonProps={{ danger: true }}
                      onConfirm={() => deleteKeyMut.mutate(record.id)}
                      disabled={deleteKeyMut.isPending}
                    >
                      <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        disabled={deleteKeyMut.isPending}
                      />
                    </Popconfirm>
                  ),
                },
              ]}
            />
          )}
        </StateView>
      </Card>
      </div>
    </RoleGate>
  );
}

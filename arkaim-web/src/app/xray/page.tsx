'use client';

import { BugOutlined, ReloadOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute, RoleGuard } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LTabs } from '@/shared/ui/light/LTabs';
import { LTable } from '@/shared/ui/light/LTable';
import { LStatistic } from '@/shared/ui/light/LStatistic';
import { LTag } from '@/shared/ui/light/LTag';

type Trace = {
  trace_id: string;
  name: string;
  status: string;
  duration_ms: number;
  started_at: string;
  ended_at?: string;
};

type XRayStats = {
  active_traces: number;
  completed_traces: number;
  orphan_spans: number;
};

function StatsPanel() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['xray-stats'],
    queryFn: () => api.get<XRayStats>('/xray/stats'),
  });

  if (isLoading) return <LSpin />;

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 200px' }}>
        <LCard><LStatistic title="Активных трейсов" value={stats?.active_traces ?? 0} prefix={<ReloadOutlined />} /></LCard>
      </div>
      <div style={{ flex: '1 1 200px' }}>
        <LCard><LStatistic title="Завершённых" value={stats?.completed_traces ?? 0} prefix={<ClockCircleOutlined />} /></LCard>
      </div>
      <div style={{ flex: '1 1 200px' }}>
        <LCard><LStatistic title="Сиротских спанов" value={stats?.orphan_spans ?? 0} prefix={<BugOutlined />} /></LCard>
      </div>
    </div>
  );
}

function TracesPanel() {
  const { data: traces, isLoading } = useQuery({
    queryKey: ['xray-traces'],
    queryFn: () => api.get<Trace[]>('/xray/traces?limit=50'),
    staleTime: 10_000,
    refetchInterval: 15_000,
  });

  const columns = [
    {
      title: 'ID', dataIndex: 'trace_id', key: 'id',
      render: (v: unknown) => <code style={{ fontSize: 11 }}>{(v as string).slice(0, 12)}...</code>,
    },
    { title: 'Имя', dataIndex: 'name', key: 'name' },
    {
      title: 'Статус', dataIndex: 'status', key: 'status',
      render: (v: unknown) => (
        <LTag color={v === 'ok' ? 'green' : v === 'error' ? 'red' : 'blue'}>{v as string}</LTag>
      ),
    },
    {
      title: 'Длительность', dataIndex: 'duration_ms', key: 'duration',
      render: (v: unknown) => (v as number) ? `${Math.round(v as number)}ms` : '—',
    },
    {
      title: 'Начало', dataIndex: 'started_at', key: 'started',
      render: (v: unknown) => (v as string) ? new Date(v as string).toLocaleString('ru') : '—',
    },
  ];

  return (
    <LTable
      columns={columns}
      dataSource={traces || []}
      rowKey="trace_id"
      loading={isLoading}
      size="small"
      pagination={{ pageSize: 20 }}
    />
  );
}

function DiagnosticsPanel() {
  const { data: diag, isLoading } = useQuery({
    queryKey: ['xray-diagnostics'],
    queryFn: () => api.get<Record<string, unknown>>('/xray/diagnostics'),
  });

  if (isLoading) return <LSpin />;

  return (
    <LCard>
      <div style={{ fontWeight: 600, fontSize: 14 }}>Диагностика системы</div>
      <div style={{ marginTop: 12 }}>
        {diag && Object.entries(diag).map(([key, value]) => (
          <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f1f5f9' }}>
            <span>{key}</span>
            <span style={{ color: '#666' }}>{String(value)}</span>
          </div>
        ))}
      </div>
    </LCard>
  );
}

function XRayContent() {
  const items = [
    { key: 'stats', label: <><ReloadOutlined /> Статистика</>, children: <StatsPanel /> },
    { key: 'traces', label: <><BugOutlined /> Трейсы</>, children: <TracesPanel /> },
    { key: 'diagnostics', label: 'Диагностика', children: <DiagnosticsPanel /> },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <h2><BugOutlined /> X-Ray Observability</h2>
      <LTabs items={items} />
    </div>
  );
}

export default function XRayPage() {
  return (
    <ProtectedRoute>
      <RoleGuard roles={['admin']}>
        <XRayContent />
      </RoleGuard>
    </ProtectedRoute>
  );
}
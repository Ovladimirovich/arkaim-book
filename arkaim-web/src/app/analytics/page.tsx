'use client';

function BarChart({ data, height = 200 }: { data: { label: string; value: number }[]; height?: number }) {
  const maxValue = Math.max(...data.map(d => d.value));
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height, padding: '20px 0' }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ width: '100%', height: `${(d.value / maxValue) * (height - 40)}px`, background: 'linear-gradient(180deg, #1890ff 0%, #096dd9 100%)', borderRadius: '4px 4px 0 0' }} />
          <span style={{ fontSize: 10, marginTop: 4 }}>{d.label}</span>
        </div>
      ))}
    </div>
  );
}

import { BarChartOutlined, LineChartOutlined, PieChartOutlined, RiseOutlined, DatabaseOutlined, ApiOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LStatistic } from '@/shared/ui/light/LStatistic';
import { LTable } from '@/shared/ui/light/LTable';
import { LProgress } from '@/shared/ui/light/LProgress';
import { LDivider } from '@/shared/ui/light/LDivider';

type AnalyticsData = {
  total_requests: number;
  requests_by_type: Record<string, number>;
  requests_by_hour: Record<string, number>;
  avg_response_time_ms: number;
  error_rate: number;
};

type GraphStats = {
  nodes: number;
  edges: number;
  node_types: Record<string, number>;
  relationship_types: Record<string, number>;
};

type AdminStats = {
  users: { total: number; by_role: Record<string, number> };
  presence: { trending_topics: number; pending_suggestions: number };
  email: Record<string, unknown>;
};

function RequestAnalyticsPanel({ data }: { data: AnalyticsData }) {
  const topTypes = Object.entries(data.requests_by_type || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const topHours = Object.entries(data.requests_by_hour || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 400px' }}>
        <LCard title="Запросы по типу" size="small">
          {topTypes.length > 0 ? (
            <LTable
              dataSource={topTypes.map(([type, count]) => ({ type, count, percent: data.total_requests > 0 ? Math.round(count / data.total_requests * 100) : 0 }))}
              rowKey="type"
              size="small"
              pagination={false}
              columns={[
                { title: 'Тип', dataIndex: 'type', key: 'type' },
                {
                  title: 'Количество', dataIndex: 'count', key: 'count',
                  sorter: (a: unknown, b: unknown) => (a as { count: number }).count - (b as { count: number }).count,
                },
                {
                  title: '%', dataIndex: 'percent', key: 'percent',
                  render: (v: unknown) => <LProgress percent={v as number} size="small" showInfo={false} />,
                },
              ]}
            />
          ) : (
            <span style={{ color: '#999' }}>Нет данных</span>
          )}
        </LCard>
      </div>
      <div style={{ flex: '1 1 400px' }}>
        <LCard title="Запросы по часам" size="small">
          {topHours.length > 0 ? (
            <LTable
              dataSource={topHours.map(([hour, count]) => ({ hour: `${hour}:00`, count }))}
              rowKey="hour"
              size="small"
              pagination={false}
              columns={[
                { title: 'Час', dataIndex: 'hour', key: 'hour' },
                {
                  title: 'Количество', dataIndex: 'count', key: 'count',
                  sorter: (a: unknown, b: unknown) => (a as { count: number }).count - (b as { count: number }).count,
                },
              ]}
            />
          ) : (
            <span style={{ color: '#999' }}>Нет данных</span>
          )}
        </LCard>
      </div>
    </div>
  );
}

function GraphStatsPanel({ data }: { data: GraphStats }) {
  const nodeTypes = Object.entries(data.node_types || {}).map(([type, count]) => ({ type, count }));
  const relTypes = Object.entries(data.relationship_types || {}).map(([type, count]) => ({ type, count }));

  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 200px' }}>
        <LCard size="small">
          <LStatistic title="Узлов" value={data.nodes} prefix={<DatabaseOutlined />} />
        </LCard>
      </div>
      <div style={{ flex: '1 1 200px' }}>
        <LCard size="small">
          <LStatistic title="Связей" value={data.edges} prefix={<ApiOutlined />} />
        </LCard>
      </div>
      <div style={{ flex: '1 1 200px' }}>
        <LCard size="small">
          <LStatistic title="Типов узлов" value={Object.keys(data.node_types || {}).length} />
        </LCard>
      </div>
      <div style={{ flex: '1 1 400px' }}>
        <LCard title="Типы узлов" size="small">
          <LTable
            dataSource={nodeTypes}
            rowKey="type"
            size="small"
            pagination={false}
            columns={[
              { title: 'Тип', dataIndex: 'type', key: 'type' },
              { title: 'Количество', dataIndex: 'count', key: 'count' },
            ]}
          />
        </LCard>
      </div>
      <div style={{ flex: '1 1 400px' }}>
        <LCard title="Типы связей" size="small">
          <LTable
            dataSource={relTypes}
            rowKey="type"
            size="small"
            pagination={false}
            columns={[
              { title: 'Тип', dataIndex: 'type', key: 'type' },
              { title: 'Количество', dataIndex: 'count', key: 'count' },
            ]}
          />
        </LCard>
      </div>
    </div>
  );
}

function SystemStatsPanel({ analytics, adminStats }: { analytics: AnalyticsData; adminStats?: AdminStats }) {
  return (
    <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 180px' }}>
        <LCard size="small">
          <LStatistic title="Всего запросов" value={analytics.total_requests} prefix={<BarChartOutlined />} />
        </LCard>
      </div>
      <div style={{ flex: '1 1 180px' }}>
        <LCard size="small">
          <LStatistic
            title="Среднее время"
            value={Math.round(analytics.avg_response_time_ms)}
            suffix="ms"
            prefix={<LineChartOutlined />}
          />
        </LCard>
      </div>
      <div style={{ flex: '1 1 180px' }}>
        <LCard size="small">
          <LStatistic
            title="Ошибка"
            value={analytics.error_rate}
            suffix="%"
            valueStyle={{ color: analytics.error_rate > 5 ? '#ef4444' : '#16a34a' }}
          />
        </LCard>
      </div>
      <div style={{ flex: '1 1 180px' }}>
        <LCard size="small">
          <LStatistic title="Пользователей" value={adminStats?.users?.total ?? 0} />
        </LCard>
      </div>
    </div>
  );
}

function AnalyticsContent() {
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => api.get<AnalyticsData>('/analytics'),
  });

  const { data: graphStats, isLoading: graphLoading } = useQuery({
    queryKey: ['graph-stats'],
    queryFn: () => api.get<GraphStats>('/book/graph/stats'),
  });

  const { data: adminStats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => api.get<AdminStats>('/auth/admin/stats'),
  });

  if (analyticsLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <LSpin size="large" />
        <div style={{ marginTop: 16, color: '#999' }}>Загрузка аналитики...</div>
      </div>
    );
  }

  if (!analytics) {
    return <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>Данные аналитики недоступны</div>;
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <h2><RiseOutlined /> Аналитика</h2>
      <p style={{ color: '#666' }}>Статистика использования системы и знаний</p>

      <SystemStatsPanel analytics={analytics} adminStats={adminStats} />

      <LDivider />

      <h4>Запросы</h4>
      <RequestAnalyticsPanel data={analytics} />

      <LDivider />

      <h4>Граф знаний</h4>
      {graphLoading ? <LSpin /> : graphStats ? <GraphStatsPanel data={graphStats} /> : <span style={{ color: '#999' }}>Нет данных</span>}
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <ProtectedRoute>
      <AnalyticsContent />
    </ProtectedRoute>
  );
}
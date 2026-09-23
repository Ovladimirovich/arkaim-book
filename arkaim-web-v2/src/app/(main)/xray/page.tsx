/**
 * /xray — observability dashboard (F5).
 *
 * Контракты:
 *   GET /xray/version  → direct {version, build}
 *   GET /xray/stats    → direct {active_traces, completed_traces}
 *   GET /xray/events   → direct XrayEventItem[]
 *   SSE   /xray/events/stream → typed events (consumeSseResponse)
 */
'use client';

import { Card, Col, Row, Statistic, Tag, Typography, List, Space } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { SyncOutlined, CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { getXrayVersion, getXrayStats, getXrayEvents, type XrayEventItem } from '@/shared/api/contracts/xray';
import { useXraySseBuffer } from '@/shared/realtime/xray-sse';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text } = Typography;

// ── Helpers ───────────────────────────────────────────────

function eventColor(event: string): string {
  switch (event) {
    case 'trace_completed': return 'green';
    case 'trace_frozen': return 'gold';
    case 'trace_terminated': return 'red';
    case 'orphan_change': return 'purple';
    case 'stats_changed': return 'blue';
    case 'heartbeat': return 'default';
    default: return 'default';
  }
}

function eventLabel(event: string): string {
  switch (event) {
    case 'trace_completed': return 'Trace completed';
    case 'trace_frozen': return 'Trace frozen';
    case 'trace_terminated': return 'Trace terminated';
    case 'orphan_change': return 'Orphan changed';
    case 'stats_changed': return 'Stats changed';
    case 'heartbeat': return 'Heartbeat';
    default: return event;
  }
}

function fmtTime(ts: number): string {
  return new Date(ts).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// ── Page ──────────────────────────────────────────────────

export default function XrayPage() {
  const version = useQuery({
    queryKey: ['xray', 'version'],
    queryFn: getXrayVersion,
    staleTime: 5 * 60 * 1000,
  });

  const stats = useQuery({
    queryKey: ['xray', 'stats'],
    queryFn: getXrayStats,
    staleTime: 10_000,
    refetchInterval: 10_000,
  });

  const events = useQuery({
    queryKey: ['xray', 'events'],
    queryFn: () => getXrayEvents(50),
    staleTime: 30_000,
  });

  // SSE live buffer
  const liveBuffer = useXraySseBuffer({
    onEvent: () => {
      // trigger refetch of stats on meaningful events
    },
  });

  // Merge historical events with live buffer
  const allEvents = [...(events.data ?? []), ...liveBuffer.map((m) => ({
    trace_id: m.data.trace_id ?? '',
    event: m.event,
    timestamp: new Date(m.timestamp).toISOString(),
    duration_ms: m.data.duration_ms,
    name: m.data.name,
  }))].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        X-Ray Observability
      </Title>

      {/* ── Stats row ── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={stats.data}
              loading={stats.isLoading}
              error={(stats.error as ApiError | null) ?? null}
              onRetry={() => void stats.refetch()}
            >
              {(d) => (
                <Statistic
                  title="Активных трейсов"
                  value={d.active_traces}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ color: d.active_traces > 0 ? '#faad14' : '#52c41a' }}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Завершённых трейсов"
              value={stats.data?.completed_traces ?? 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={version.data}
              loading={version.isLoading}
              error={(version.error as ApiError | null) ?? null}
              onRetry={() => void version.refetch()}
            >
              {(d) => (
                <Statistic
                  title="X-Ray версия"
                  value={d.version}
                  suffix={<Tag>build {d.build ?? '?'}</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Live событий"
              value={liveBuffer.length}
              prefix={<SyncOutlined spin={liveBuffer.length > 0} />}
              valueStyle={{ color: liveBuffer.length > 0 ? '#1677ff' : '#8c8c8c' }}
            />
          </Card>
        </Col>
      </Row>

      {/* ── Live SSE feed ── */}
      <Card
        title={
          <Space>
            <SyncOutlined spin={liveBuffer.length > 0} />
            <span>Live лента трасировок</span>
            <Tag color={liveBuffer.length > 0 ? 'green' : 'default'}>
              {liveBuffer.length > 0 ? 'online' : 'idle'}
            </Tag>
          </Space>
        }
        size="small"
      >
        {allEvents.length === 0 ? (
          <Text type="secondary" style={{ fontSize: 13 }}>
            Ожидание событий…
          </Text>
        ) : (
          <List
            size="small"
            dataSource={allEvents.slice(0, 50)}
            renderItem={(e) => (
              <List.Item>
                <Space size={8}>
                  <Tag color={eventColor(e.event)} style={{ minWidth: 100 }}>
                    {eventLabel(e.event)}
                  </Tag>
                  {e.trace_id && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {e.trace_id.slice(0, 8)}…
                    </Text>
                  )}
                  {e.duration_ms !== undefined && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {e.duration_ms}ms
                    </Text>
                  )}
                  <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
                    {new Date(e.timestamp).toLocaleTimeString('ru-RU')}
                  </Text>
                </Space>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}

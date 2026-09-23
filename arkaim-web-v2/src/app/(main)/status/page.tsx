/**
 * /status — системный статус (F1-foundation-дашборд; перенесён с «/» в F2).
 * Домашний экран «/» — вертикаль «Спросить книгу» (F2_SPEC §1).
 */
'use client';

import { Card, Col, Row, Statistic, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getHealth, ApiError } from '@/shared/api';
import { RBAC_ROUTES_TOTAL, RBAC_SNAPSHOT_DATE } from '@/shared/rbac/generated/matrix';
import { useWsStatus } from '@/shared/realtime/WsProvider';
import { StateView } from '@/shared/ui/StateView';

export default function StatusPage() {
  const ws = useWsStatus();
  const health = useQuery({
    queryKey: ['system', 'health'],
    queryFn: () => getHealth(),
    staleTime: 30_000,
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        Статус системы
      </Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Card>
            <StateView
              data={health.data}
              loading={health.isLoading}
              error={health.error as ApiError | null}
              onRetry={() => void health.refetch()}
            >
              {(h) => (
                <Statistic
                  title="Backend /health"
                  value={h.status}
                  valueStyle={{ color: h.status === 'ok' ? '#52c41a' : '#cf1322' }}
                  suffix={<Tag style={{ marginLeft: 8 }}>{h.mode ? `режим ${h.mode}` : ''}</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Контрактов OpenAPI" value={289} suffix="путей (слепок)" />
            <Statistic
              title="RBAC-маршрутов в матрице"
              value={RBAC_ROUTES_TOTAL}
              suffix={<Tag>{RBAC_SNAPSHOT_DATE}</Tag>}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Realtime /ws"
              value={ws.connected ? 'онлайн' : 'нет связи'}
              valueStyle={{ color: ws.connected ? '#52c41a' : '#8c8c8c' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

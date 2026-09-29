'use client';

import { Card, Row, Col, Statistic } from 'antd';
import { TeamOutlined, KeyOutlined, BarChartOutlined } from '@ant-design/icons';

export function StatsPanel() {
  return (
    <Row gutter={16}>
      <Col span={8}>
        <Card>
          <Statistic title="Пользователей" value={42} prefix={<TeamOutlined />} />
        </Card>
      </Col>
      <Col span={8}>
        <Card>
          <Statistic title="API ключей" value={12} prefix={<KeyOutlined />} />
        </Card>
      </Col>
      <Col span={8}>
        <Card>
          <Statistic title="Запросов сегодня" value={1247} prefix={<BarChartOutlined />} />
        </Card>
      </Col>
    </Row>
  );
}

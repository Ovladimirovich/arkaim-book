'use client';

import { Tag, Tooltip } from 'antd';
import { DatabaseOutlined, ThunderboltOutlined, LinkOutlined, BulbOutlined } from '@ant-design/icons';

const SOURCE_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pulse: { icon: <DatabaseOutlined />, color: '#059669', label: 'Геном' },
  llm: { icon: <ThunderboltOutlined />, color: '#7c3aed', label: 'AI' },
  hybrid: { icon: <LinkOutlined />, color: '#2563eb', label: 'Гибрид' },
  mock: { icon: <BulbOutlined />, color: '#6b7280', label: 'Заглушка' },
};

export function SourceBadge({ sourceType }: { sourceType?: string }) {
  if (!sourceType) return null;
  const config = SOURCE_CONFIG[sourceType] || SOURCE_CONFIG.mock;
  return (
    <Tooltip title={`Источник: ${config.label}`}>
      <Tag style={{ marginTop: 4, fontSize: 10, color: config.color, borderColor: config.color }}>
        {config.icon} {config.label}
      </Tag>
    </Tooltip>
  );
}

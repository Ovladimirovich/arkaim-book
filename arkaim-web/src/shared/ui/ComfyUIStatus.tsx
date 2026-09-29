'use client';

import React from 'react';
import { Tag, Tooltip, Spin } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';

type ComfyUIStatusData = {
  status: 'connected' | 'disconnected' | 'error';
  url?: string;
  provider?: string;
  error?: string;
};

export function ComfyUIStatus() {
  const { data, isLoading } = useQuery<ComfyUIStatusData>({
    queryKey: ['comfyui-status'],
    queryFn: async () => {
      try {
        return await api.get('/book/comfyui/status');
      } catch {
        return { status: 'error', error: 'Failed to check' };
      }
    },
    refetchInterval: 30000,
    retry: false,
  });

  if (isLoading) {
    return <Tag icon={<LoadingOutlined />} color="processing">Проверка...</Tag>;
  }

  const status = data?.status || 'error';
  const color = status === 'connected' ? 'success' : status === 'disconnected' ? 'warning' : 'error';
  const icon = status === 'connected'
    ? <CheckCircleOutlined />
    : <CloseCircleOutlined />;
  const label = status === 'connected' ? 'ComfyUI Online' : status === 'disconnected' ? 'ComfyUI Offline' : 'ComfyUI Error';

  return (
    <Tooltip title={data?.url ? `URL: ${data.url}` : data?.error || 'Unknown'}>
      <Tag icon={icon} color={color}>{label}</Tag>
    </Tooltip>
  );
}

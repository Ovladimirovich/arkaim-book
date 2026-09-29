'use client';

import React from 'react';

interface LBadgeProps {
  children?: React.ReactNode;
  count?: React.ReactNode;
  showZero?: boolean;
  color?: string;
  dot?: boolean;
  status?: 'success' | 'processing' | 'error' | 'default' | 'warning';
  text?: React.ReactNode;
  style?: React.CSSProperties;
}

const STATUS_COLORS: Record<string, string> = {
  success: '#52c41a',
  processing: '#1677ff',
  error: '#ff4d4f',
  warning: '#faad14',
  default: '#d9d9d9',
};

export function LBadge({ children, count, showZero = false, color, dot, status, text, style }: LBadgeProps) {
  const badgeColor = status ? STATUS_COLORS[status] : color || '#ff4d4f';
  const showBadge = dot || (count !== undefined && ((typeof count === 'number' && count > 0) || (typeof count !== 'number' && count !== false) || showZero));

  const badge = showBadge ? (
    <span
      style={{
        position: 'absolute',
        top: -2,
        right: -2,
        minWidth: dot ? 6 : 16,
        height: dot ? 6 : 16,
        padding: dot ? 0 : '0 4px',
        fontSize: 10,
        lineHeight: dot ? '6px' : '16px',
        borderRadius: dot ? '50%' : 8,
        background: badgeColor,
        color: '#fff',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        transform: 'translate(50%, -50%)',
        transformOrigin: '100% 0%',
      }}
    >
      {!dot && count}
    </span>
  ) : null;

  if (text !== undefined) {
    return (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, position: 'relative', ...style }}>
        {badge}
        {text}
      </span>
    );
  }

  if (!children) return badge;

  return (
    <span style={{ position: 'relative', display: 'inline-block', ...style }}>
      {children}
      {badge}
    </span>
  );
}

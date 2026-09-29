'use client';

import React from 'react';

const COLORS: Record<string, { bg: string; text: string }> = {
  red: { bg: '#fff1f0', text: '#ff4d4f' },
  green: { bg: '#f6ffed', text: '#52c41a' },
  blue: { bg: '#e6f7ff', text: '#1677ff' },
  orange: { bg: '#fff7e6', text: '#faad14' },
  purple: { bg: '#f9f0ff', text: '#722ed1' },
  cyan: { bg: '#e6fffb', text: '#13c2c2' },
  gold: { bg: '#fffbe6', text: '#faad14' },
  lime: { bg: '#fcffe6', text: '#a0d911' },
  geekblue: { bg: '#f0f5ff', text: '#2f54eb' },
  magenta: { bg: '#fff0f6', text: '#eb2f96' },
  default: { bg: 'var(--card-border)', text: 'var(--foreground)' },
  processing: { bg: '#e6f7ff', text: '#1677ff' },
  success: { bg: '#f6ffed', text: '#52c41a' },
  error: { bg: '#fff2f0', text: '#ff4d4f' },
  warning: { bg: '#fffbe6', text: '#faad14' },
};

interface LTagProps {
  children: React.ReactNode;
  color?: string;
  icon?: React.ReactNode;
  style?: React.CSSProperties;
  className?: string;
  onClick?: () => void;
  title?: string;
}

export function LTag({ children, color, icon, style, className, onClick, title }: LTagProps) {
  const colorKey = color || 'default';
  const colors = COLORS[colorKey] || COLORS.default;

  return (
    <span
      className={className}
      title={title}
      onClick={onClick}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '0 7px',
        fontSize: 12,
        lineHeight: '20px',
        borderRadius: 4,
        border: `1px solid ${colors.text}`,
        color: colors.text,
        background: colors.bg,
        whiteSpace: 'nowrap',
        cursor: onClick ? 'pointer' : undefined,
        ...style,
      }}
    >
      {icon && <span style={{ fontSize: 11 }}>{icon}</span>}
      {children}
    </span>
  );
}
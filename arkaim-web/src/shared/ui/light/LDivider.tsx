'use client';

import React from 'react';

interface LDividerProps {
  type?: 'horizontal' | 'vertical';
  children?: React.ReactNode;
  plain?: boolean;
  orientation?: 'left' | 'center' | 'right';
  dashed?: boolean;
  style?: React.CSSProperties;
}

export function LDivider({ type = 'horizontal', children, plain, orientation = 'center', dashed, style }: LDividerProps) {
  if (type === 'vertical') {
    return (
      <span
        style={{
          display: 'inline-block',
          width: 1,
          height: '1em',
          margin: '0 8px',
          verticalAlign: 'middle',
          background: 'var(--divider-color)',
          ...style,
        }}
      />
    );
  }

  if (children) {
    const flexAlign = orientation === 'left' ? 'flex-start' : orientation === 'right' ? 'flex-end' : 'center';
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '16px 0', ...style }}>
        <div style={{ flex: 1, borderTop: `1px solid ${dashed ? 'dashed' : 'solid'} var(--divider-color)` }} />
        <span style={{ fontSize: plain ? 12 : 13, color: '#999', whiteSpace: 'nowrap', fontWeight: plain ? 400 : 500 }}>
          {children}
        </span>
        <div style={{ flex: 1, borderTop: `1px solid ${dashed ? 'dashed' : 'solid'} var(--divider-color)` }} />
      </div>
    );
  }

  return (
    <div
      style={{
        margin: '16px 0',
        borderTop: `${dashed ? 'dashed' : 'solid'} 1px var(--divider-color)`,
        ...style,
      }}
    />
  );
}
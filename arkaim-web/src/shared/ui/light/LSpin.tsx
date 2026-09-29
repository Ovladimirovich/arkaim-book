'use client';

import React from 'react';

interface LSpinProps {
  size?: 'small' | 'default' | 'large';
  tip?: string;
  spinning?: boolean;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

const SIZES = { small: 12, default: 20, large: 32 };

export function LSpin({ size = 'default', tip, spinning = true, children, style }: LSpinProps) {
  if (!spinning) return <>{children}</>;

  const px = SIZES[size];

  const spinner = (
    <span
      style={{
        display: 'inline-block',
        width: px,
        height: px,
        border: `${Math.max(2, px / 8)}px solid #f0f0f0`,
        borderTopColor: '#1677ff',
        borderRadius: '50%',
        animation: 'lspin 0.8s linear infinite',
        ...style,
      }}
    />
  );

  if (children) {
    return (
      <span style={{ position: 'relative', display: 'inline-block' }}>
        <span style={{ opacity: 0.5, pointerEvents: 'none' }}>{children}</span>
        <span style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}>
          {spinner}
        </span>
      </span>
    );
  }

  return (
    <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      {spinner}
      {tip && <span style={{ fontSize: 14, color: '#666' }}>{tip}</span>}
    </span>
  );
}

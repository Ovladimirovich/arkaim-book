'use client';

import React from 'react';

interface LSegmentedOption {
  label: React.ReactNode;
  value: string | number;
}

interface LSegmentedProps {
  options: LSegmentedOption[];
  value?: string | number;
  onChange?: (value: string | number) => void;
  size?: 'small' | 'middle' | 'large';
  style?: React.CSSProperties;
}

const SIZES = { small: 24, middle: 32, large: 40 };

export function LSegmented({ options, value, onChange, size = 'middle', style }: LSegmentedProps) {
  const height = SIZES[size];
  const fontSize = size === 'small' ? 12 : 14;

  return (
    <div style={{ display: 'inline-flex', border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden', ...style }}>
      {options.map(opt => {
        const isActive = value === opt.value;
        return (
          <button
            key={String(opt.value)}
            onClick={() => onChange?.(opt.value)}
            style={{
              padding: `0 ${height === 24 ? 7 : 12}px`,
              height,
              fontSize,
              border: 'none',
              background: isActive ? '#1677ff' : 'var(--surface-bg)',
              color: isActive ? '#fff' : 'var(--foreground)',
              cursor: 'pointer',
              transition: 'all 0.2s',
              borderRight: '1px solid var(--input-border)',
            }}
          >{opt.label}</button>
        );
      })}
    </div>
  );
}
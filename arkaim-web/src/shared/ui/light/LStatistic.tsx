'use client';

import React from 'react';

interface LStatisticProps {
  title?: React.ReactNode;
  value: number | string;
  precision?: number;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  valueStyle?: React.CSSProperties;
  style?: React.CSSProperties;
}

export function LStatistic({ title, value, precision, prefix, suffix, valueStyle, style }: LStatisticProps) {
  const displayValue = typeof value === 'number' && precision !== undefined ? value.toFixed(precision) : value;

  return (
    <div style={{ ...style }}>
      {title && <div style={{ fontSize: 14, color: 'var(--foreground)', marginBottom: 4, opacity: 0.65 }}>{title}</div>}
      <div style={{ fontSize: 24, fontWeight: 600, lineHeight: '32px', ...valueStyle }}>
        {prefix && <span style={{ marginRight: 4 }}>{prefix}</span>}
        {displayValue}
        {suffix && <span style={{ marginLeft: 4, fontSize: 14, color: 'var(--foreground)', opacity: 0.65 }}>{suffix}</span>}
      </div>
    </div>
  );
}
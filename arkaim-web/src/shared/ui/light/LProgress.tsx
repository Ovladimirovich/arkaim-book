'use client';

import React from 'react';

const styleId = 'lprogress-keyframes';
if (typeof document !== 'undefined' && !document.getElementById(styleId)) {
  const style = document.createElement('style');
  style.id = styleId;
  style.textContent = '@keyframes lprogress-shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }';
  document.head.appendChild(style);
}

interface LProgressProps {
  percent: number;
  type?: 'line' | 'circle';
  size?: number | 'small';
  strokeColor?: string;
  status?: 'normal' | 'success' | 'exception' | 'active';
  showInfo?: boolean;
  format?: (percent: number) => React.ReactNode;
  style?: React.CSSProperties;
}

export function LProgress({
  percent, type = 'line', size = 80, strokeColor,
  status, showInfo = true, format, style,
}: LProgressProps) {
  const color = status === 'exception' ? '#ff4d4f' : status === 'success' ? '#52c41a' : strokeColor || '#1677ff';
  const clampedPercent = Math.max(0, Math.min(100, percent));
  const isActive = status === 'active';

  if (type === 'circle') {
    const numericSize = typeof size === 'number' ? size : 80;
    const radius = (numericSize - 8) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference * (1 - clampedPercent / 100);

    return (
      <div style={{ position: 'relative', width: numericSize, height: numericSize, ...style }}>
        <svg width={numericSize} height={numericSize} viewBox={`0 0 ${numericSize} ${numericSize}`}>
          <circle cx={numericSize / 2} cy={numericSize / 2} r={radius} fill="none" stroke="var(--divider-color)" strokeWidth="6" />
          <circle
            cx={numericSize / 2} cy={numericSize / 2} r={radius}
            fill="none" stroke={color} strokeWidth="6"
            strokeDasharray={circumference} strokeDashoffset={offset}
            transform={`rotate(-90 ${numericSize / 2} ${numericSize / 2})`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.3s' }}
          />
        </svg>
        {showInfo && (
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: numericSize / 5, fontWeight: 600 }}>
            {format ? format(clampedPercent) : `${clampedPercent}%`}
          </div>
        )}
      </div>
    );
  }

  const barHeight = size === 'small' ? 6 : 8;
  const infoSize = size === 'small' ? 10 : 12;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, ...style }}>
      <div style={{ flex: 1, height: barHeight, background: 'var(--divider-color)', borderRadius: 4, overflow: 'hidden' }}>
        <div
          style={{
            width: `${clampedPercent}%`,
            height: '100%',
            background: color,
            borderRadius: 4,
            transition: 'width 0.3s',
            ...(isActive ? { backgroundImage: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)', backgroundSize: '200% 100%', animation: 'lprogress-shimmer 1.5s infinite' } : {}),
          }}
        />
      </div>
      {showInfo && (
        <span style={{ fontSize: infoSize, color: 'var(--foreground)', minWidth: 32, textAlign: 'right' }}>
          {format ? format(clampedPercent) : `${clampedPercent}%`}
        </span>
      )}
    </div>
  );
}
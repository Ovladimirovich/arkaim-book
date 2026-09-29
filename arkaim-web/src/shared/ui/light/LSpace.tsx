'use client';

import React from 'react';

interface LSpaceProps {
  children: React.ReactNode;
  direction?: 'horizontal' | 'vertical';
  size?: number | 'small' | 'middle' | 'large';
  wrap?: boolean;
  style?: React.CSSProperties;
}

const SIZES = { small: 4, middle: 8, large: 16 };

export function LSpace({ children, direction = 'horizontal', size = 8, wrap, style }: LSpaceProps) {
  const gap = typeof size === 'number' ? size : SIZES[size] || 8;
  const isVertical = direction === 'vertical';

  return (
    <span
      style={{
        display: 'inline-flex',
        flexDirection: isVertical ? 'column' : 'row',
        gap: isVertical ? gap : gap,
        flexWrap: wrap ? 'wrap' : undefined,
        alignItems: isVertical ? undefined : 'center',
        ...style,
      }}
    >
      {React.Children.map(children, (child, i) =>
        child != null && child !== false ? (
          <span key={i} style={isVertical ? { marginRight: 0 } : { marginRight: i < React.Children.count(children) - 1 ? gap : 0 }}>
            {child}
          </span>
        ) : null
      )}
    </span>
  );
}

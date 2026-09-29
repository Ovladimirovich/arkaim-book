'use client';

import React from 'react';

interface LAvatarProps {
  children?: React.ReactNode;
  size?: number;
  shape?: 'circle' | 'square';
  style?: React.CSSProperties;
  src?: string;
  alt?: string;
}

export function LAvatar({ children, size = 40, shape = 'circle', style, src, alt }: LAvatarProps) {
  const borderRadius = shape === 'circle' ? '50%' : size * 0.25;

  if (src) {
    return (
      <img
        src={src}
        alt={alt || ''}
        style={{ width: size, height: size, borderRadius, objectFit: 'cover', ...style }}
      />
    );
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: size,
        height: size,
        borderRadius,
        fontSize: size * 0.45,
        fontWeight: 600,
        background: '#d9d9d9',
        color: '#fff',
        overflow: 'hidden',
        flexShrink: 0,
        ...style,
      }}
    >
      {children}
    </span>
  );
}
'use client';

import React from 'react';

interface LCardProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  extra?: React.ReactNode;
  size?: 'small' | 'default';
  style?: React.CSSProperties;
  className?: string;
  hoverable?: boolean;
  bordered?: boolean;
  onClick?: () => void;
  cover?: React.ReactNode;
  actions?: React.ReactNode[];
}

export const LCard = React.forwardRef<HTMLDivElement, LCardProps>(({ children, title, extra, size = 'default', style, className, hoverable, bordered = true, onClick, cover, actions }, ref) => {
  const padding = size === 'small' ? 12 : 20;

  return (
    <div
      className={className}
      ref={ref}
      onClick={onClick}
      style={{
        background: 'var(--card-bg)',
        borderRadius: 8,
        border: bordered ? '1px solid var(--card-border)' : 'none',
        transition: hoverable ? 'box-shadow 0.2s' : undefined,
        cursor: onClick ? 'pointer' : hoverable ? 'pointer' : undefined,
        ...style,
      }}
      onMouseEnter={hoverable ? (e) => { (e.currentTarget as HTMLElement).style.boxShadow = '0 1px 4px rgba(0,0,0,0.12)'; } : undefined}
      onMouseLeave={hoverable ? (e) => { (e.currentTarget as HTMLElement).style.boxShadow = 'none'; } : undefined}
    >
      {cover && <div style={{ overflow: 'hidden' }}>{cover}</div>}
      {(title || extra) && (
        <div style={{ padding: `${padding / 2}px ${padding}px`, borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {title && <div style={{ fontWeight: 500, fontSize: 14 }}>{title}</div>}
          {extra && <div>{extra}</div>}
        </div>
      )}
      <div style={{ padding }}>{children}</div>
      {actions && actions.length > 0 && (
        <div style={{ borderTop: '1px solid var(--card-border)', display: 'flex', justifyContent: 'center', gap: 8, padding: `${padding / 2}px ${padding}px` }}>
          {actions.filter(Boolean).map((action, i) => <div key={i}>{action}</div>)}
        </div>
      )}
    </div>
  );
});

LCard.displayName = 'LCard';
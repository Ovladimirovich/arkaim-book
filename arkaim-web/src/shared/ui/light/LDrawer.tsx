'use client';

import React, { useEffect } from 'react';

interface LDrawerProps {
  open: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  placement?: 'left' | 'right';
  width?: number;
  extra?: React.ReactNode;
  style?: React.CSSProperties;
}

export function LDrawer({ open, onClose, title, children, placement = 'left', width = 280, extra, style }: LDrawerProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = ''; };
    }
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        onClick={onClose}
        style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 999, background: 'var(--modal-mask)' }}
      />
      <div
        style={{
          position: 'fixed', top: 0, bottom: 0,
          [placement]: 0,
          zIndex: 1000,
          width,
          background: 'var(--surface-bg)',
          boxShadow: placement === 'left' ? '2px 0 8px rgba(0,0,0,0.15)' : '-2px 0 8px rgba(0,0,0,0.15)',
          display: 'flex',
          flexDirection: 'column',
          ...style,
        }}
      >
        {(title || extra) && (
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 600 }}>{title}</div>
            <div style={{ display: 'flex', gap: 8 }}>{extra}</div>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'var(--foreground)', opacity: 0.45, padding: 0, lineHeight: 1, marginLeft: 8 }}
            >✕</button>
          </div>
        )}
        {title === undefined && extra === undefined && onClose && (
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--card-border)', textAlign: 'right' }}>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'var(--foreground)', opacity: 0.45, padding: 0, lineHeight: 1 }}
            >✕</button>
          </div>
        )}
        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>{children}</div>
      </div>
    </>
  );
}
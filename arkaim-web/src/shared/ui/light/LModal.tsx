'use client';

import React, { useEffect } from 'react';

interface LModalProps {
  open: boolean;
  title?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode | null;
  onCancel?: () => void;
  width?: number;
  style?: React.CSSProperties;
}

export function LModal({ open, title, children, footer, onCancel, width = 520, style }: LModalProps) {
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = ''; };
    }
  }, [open]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onCancel?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {/* Backdrop */}
      <div
        onClick={onCancel}
        style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'var(--modal-mask)', animation: 'fadeIn 0.2s' }}
      />
      {/* Modal */}
      <div
        style={{
          position: 'relative',
          background: 'var(--surface-bg)',
          borderRadius: 8,
          boxShadow: '0 6px 16px rgba(0,0,0,0.15)',
          width: `min(${width}px, calc(100vw - 32px))`,
          maxHeight: 'calc(100vh - 64px)',
          overflow: 'auto',
          animation: 'slideUp 0.2s',
          ...style,
        }}
      >
        {/* Header */}
        {(title || onCancel) && (
          <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--card-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--foreground)' }}>{title}</div>
            {onCancel && (
              <button
                onClick={onCancel}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: 'var(--foreground)', opacity: 0.45, padding: 0, lineHeight: 1 }}
              >
                ✕
              </button>
            )}
          </div>
        )}
        {/* Body */}
        <div style={{ padding: 24 }}>{children}</div>
        {/* Footer */}
        {footer !== null && footer !== undefined && (
          <div style={{ padding: '12px 24px', borderTop: '1px solid var(--card-border)', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

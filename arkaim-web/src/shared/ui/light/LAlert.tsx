'use client';

import React from 'react';

interface LAlertProps {
  message?: React.ReactNode;
  title?: React.ReactNode;
  description?: React.ReactNode;
  type?: 'success' | 'info' | 'warning' | 'error';
  showIcon?: boolean;
  icon?: React.ReactNode;
  closable?: boolean;
  onClose?: () => void;
  style?: React.CSSProperties;
}

const COLORS = {
  success: { bg: '#f6ffed', border: '#b7eb8f', text: '#52c41a' },
  info: { bg: '#e6f7ff', border: '#91d5ff', text: '#1677ff' },
  warning: { bg: '#fffbe6', border: '#ffe58f', text: '#faad14' },
  error: { bg: '#fff2f0', border: '#ffccc7', text: '#ff4d4f' },
};

const ICONS = {
  success: '\u2714',
  info: '\u2139',
  warning: '\u26A0',
  error: '\u2718',
};

export function LAlert({ message, title, description, type = 'info', showIcon, icon, closable, onClose, style }: LAlertProps) {
  const c = COLORS[type];
  const msg = message || title;

  return (
    <div
      style={{
        padding: description || typeof msg !== 'string' ? '12px 16px' : '8px 16px',
        background: c.bg,
        border: `1px solid ${c.border}`,
        borderRadius: 6,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        ...style,
      }}
    >
      {showIcon && <span style={{ color: c.text, fontSize: 14, lineHeight: '22px' }}>{icon || ICONS[type]}</span>}
      <div style={{ flex: 1 }}>
        <div style={{ color: c.text, fontSize: description || typeof msg !== 'string' ? 14 : 13, fontWeight: description || typeof msg !== 'string' ? 500 : 400, lineHeight: '22px' }}>{msg}</div>
        {description && <div style={{ fontSize: 13, lineHeight: '22px', marginTop: typeof msg !== 'string' ? 8 : 4 }}>{description}</div>}
      </div>
      {closable && (
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: '#999', padding: 0 }}>
          \u2715
        </button>
      )}
    </div>
  );
}

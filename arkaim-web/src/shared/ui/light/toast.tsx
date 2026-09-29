'use client';

import React from 'react';

interface ToastItem {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
}

let toastId = 0;
let _setToasts: React.Dispatch<React.SetStateAction<ToastItem[]>> | null = null;

export function registerToast(setter: React.Dispatch<React.SetStateAction<ToastItem[]>>) {
  _setToasts = setter;
}

function add(type: ToastItem['type'], message: string) {
  const id = ++toastId;
  _setToasts?.(prev => [...prev, { id, message, type }]);
  setTimeout(() => {
    _setToasts?.(prev => prev.filter(t => t.id !== id));
  }, 3000);
}

export const toast = {
  success: (msg: string) => add('success', msg),
  error: (msg: string) => add('error', msg),
  warning: (msg: string) => add('warning', msg),
  info: (msg: string) => add('info', msg),
};

const COLORS = {
  success: '#52c41a',
  error: '#ff4d4f',
  warning: '#faad14',
  info: '#1677ff',
};

export function ToastContainer() {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);
  React.useEffect(() => { registerToast(setToasts); }, []);

  if (toasts.length === 0) return null;

  return (
    <div style={{ position: 'fixed', top: 16, right: 16, zIndex: 2000, display: 'flex', flexDirection: 'column', gap: 8, pointerEvents: 'none' }}>
      {toasts.map(t => (
        <div
          key={t.id}
          style={{
            padding: '10px 16px',
            borderRadius: 6,
            background: 'var(--surface-bg)',
            border: `1px solid ${COLORS[t.type]}`,
            borderLeft: `4px solid ${COLORS[t.type]}`,
            boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
            fontSize: 13,
            color: 'var(--foreground)',
            animation: 'slideIn 0.3s ease',
            pointerEvents: 'auto',
            maxWidth: 360,
          }}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
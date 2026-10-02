'use client';

import type { CSSProperties, ReactNode } from 'react';
import { LButton } from './light/LButton';
import { LEmpty } from './light/LEmpty';
import { LSpin } from './light/LSpin';

export type StateViewState = 'loading' | 'empty' | 'error';

export interface StateViewProps {
  state: StateViewState;
  title?: ReactNode;
  description?: ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  children?: ReactNode;
  style?: CSSProperties;
}

const DEFAULT_COPY: Record<StateViewState, { title: string; description: string }> = {
  loading: { title: 'Загрузка', description: 'Получаем данные…' },
  empty: { title: 'Пока пусто', description: 'Здесь появятся данные, когда они будут доступны.' },
  error: { title: 'Не удалось загрузить', description: 'Проверьте соединение и попробуйте ещё раз.' },
};

export function StateView({
  state,
  title,
  description,
  onRetry,
  retryLabel = 'Попробовать снова',
  children,
  style,
}: StateViewProps) {
  if (state === 'loading') {
    return (
      <div role="status" aria-live="polite" style={{ padding: 32, textAlign: 'center', color: 'var(--muted-foreground)', ...style }}>
        <LSpin size="small" />
        <div style={{ marginTop: 12, fontSize: 14 }}>{title ?? DEFAULT_COPY.loading.title}</div>
        {description && <div style={{ marginTop: 4, fontSize: 13 }}>{description}</div>}
      </div>
    );
  }

  if (state === 'empty') {
    return (
      <div role="status" style={style}>
        <LEmpty description={title ?? DEFAULT_COPY.empty.title} image={<span aria-hidden="true" style={{ fontSize: 32 }}>◇</span>} />
        {description && <div style={{ textAlign: 'center', color: 'var(--muted-foreground)', fontSize: 13, marginTop: -16, padding: '0 16px' }}>{description}</div>}
        {children}
      </div>
    );
  }

  return (
    <div role="alert" style={{ padding: 24, textAlign: 'center', color: 'var(--foreground)', ...style }}>
      <div style={{ color: 'var(--destructive)', fontSize: 20, marginBottom: 8 }}>!</div>
      <div style={{ fontSize: 15, fontWeight: 600 }}>{title ?? DEFAULT_COPY.error.title}</div>
      <div style={{ color: 'var(--muted-foreground)', fontSize: 13, marginTop: 6 }}>{description ?? DEFAULT_COPY.error.description}</div>
      {onRetry && <LButton onClick={onRetry} style={{ marginTop: 16 }}>{retryLabel}</LButton>}
      {children}
    </div>
  );
}
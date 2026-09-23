/**
 * StateView — единый примитив состояний loading/empty/error (F1_SPEC §8).
 * Все экраны обязаны использовать его вместо ad-hoc спиннеров.
 */
'use client';

import { Alert, Button, Skeleton, Empty as AntEmpty } from 'antd';

export function StateLoading({ lines = 3 }: { lines?: number }) {
  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} active title={false} paragraph={{ rows: 1 }} />
      ))}
    </div>
  );
}

export function StateEmpty({ description }: { description: string }) {
  return <AntEmpty description={description} style={{ padding: 32 }} />;
}

export function StateError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Alert
      type="error"
      showIcon
      message="Ошибка загрузки"
      description={message}
      action={
        onRetry ? (
          <Button size="small" danger onClick={onRetry}>
            Повторить
          </Button>
        ) : undefined
      }
      style={{ margin: 16 }}
    />
  );
}

/**
 * Универсальная обёртка: разворачивает состояния по данным.
 * error должен быть ApiError-совместимым (message).
 */
export function StateView<T>({
  data, loading, error, onRetry, empty, children,
}: {
  data: T | undefined;
  loading: boolean;
  error: { message: string } | null;
  onRetry?: () => void;
  /** Признак «пусто» (например, data === null или длина 0). */
  empty?: boolean;
  children: (data: T) => React.ReactNode;
}) {
  if (loading) return <StateLoading />;
  if (error) return <StateError message={error.message} onRetry={onRetry} />;
  if (empty) return <StateEmpty description="Нет данных" />;
  if (data === undefined || data === null) return <StateEmpty description="Нет данных" />;
  return <>{children(data)}</>;
}

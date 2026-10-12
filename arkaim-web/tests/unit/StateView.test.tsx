import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { StateView } from '@/shared/ui/StateView';

describe('StateView', () => {
  it('renders a loading state with accessible status semantics', () => {
    render(<StateView state="loading" title="Загружаем историю" description="Это может занять время" />);

    expect(screen.getByRole('status')).toBeTruthy();
    expect(screen.getByText('Загружаем историю')).toBeTruthy();
    expect(screen.getByText('Это может занять время')).toBeTruthy();
  });

  it('renders an empty state and optional custom content', () => {
    render(<StateView state="empty" title="История пуста"><button>Создать диалог</button></StateView>);

    expect(screen.getByText('История пуста')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Создать диалог' })).toBeTruthy();
  });

  it('renders an error with retry callback', () => {
    const onRetry = vi.fn();
    render(<StateView state="error" description="Сервис временно недоступен" onRetry={onRetry} />);

    expect(screen.getByRole('alert').textContent).toContain('Сервис временно недоступен');
    fireEvent.click(screen.getByRole('button', { name: 'Попробовать снова' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('omits the retry button when no onRetry is given (message is not dismissible)', () => {
    render(<StateView state="error" title="История недоступна" />);

    // Без onRetry кнопки нет вовсе: сообщение нельзя «закрыть», не повторяя запрос.
    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByRole('alert').textContent).toContain('История недоступна');
  });

  it('re-invokes onRetry on every click (repeat after restoring the connection)', () => {
    const onRetry = vi.fn();
    render(<StateView state="error" title="Ошибка" onRetry={onRetry} />);

    const button = screen.getByRole('button', { name: 'Попробовать снова' });
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);

    expect(onRetry).toHaveBeenCalledTimes(3);
  });
});
/**
 * Unit-тест рендеринга EntityCard — плашки связанной сущности под ответом книги.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EntityCard } from '@/shared/ui/EntityCard';

const push = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, prefetch: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

describe('EntityCard', () => {
  beforeEach(() => {
    push.mockClear();
  });

  it('рендерит имя, категорию и кнопки World / Temporal', () => {
    render(
      <EntityCard
        entity={{ entity_id: 'char_velik', entity_type: 'character', name: 'Велик', description: 'Главный герой' }}
        sessionId="sess-1"
      />,
    );

    expect(screen.getByText('Велик')).toBeTruthy();
    expect(screen.getByText('character')).toBeTruthy();
    expect(screen.getByText('Открыть в World →')).toBeTruthy();
    expect(screen.getByText('Временной контекст →')).toBeTruthy();
  });

  it('навигирует на существующий маршрут /world-engine с entity_id и session', () => {
    render(<EntityCard entity={{ entity_id: 'loc_arkaim', name: 'Аркаим' }} sessionId="sess-42" />);

    fireEvent.click(screen.getByText('Открыть в World →'));
    // Существующий маршрут World в arkaim-web — /world-engine (не вымышленный /world)
    expect(push).toHaveBeenCalledWith('/world-engine?entity_id=loc_arkaim&session=sess-42');
  });

  it('навигирует из EntityCard в /temporal с entity и session', () => {
    render(<EntityCard entity={{ entity_id: 'char_velik', name: 'Велик' }} sessionId="sess-42" />);

    fireEvent.click(screen.getByText('Временной контекст →'));
    expect(push).toHaveBeenCalledWith('/temporal?entity=char_velik&session=sess-42');
  });
});

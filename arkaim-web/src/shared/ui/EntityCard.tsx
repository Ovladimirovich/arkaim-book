'use client';

/**
 * EntityCard — интерактивная плашка связанной сущности под ответом книги.
 *
 * Отображает имя, категорию и краткое описание сущности, а также кнопку
 * перехода в World. Клик навигирует на существующий маршрут /world-engine
 * с query-параметром entity_id (глубокая ссылка обрабатывается страницей
 * World Engine через её же контракт GET /book/world/entity/{id}/context).
 * Дополнительно передаётся session_id для сквозной истории навигации.
 */

import { useRouter } from 'next/navigation';
import { ClockCircleOutlined, GlobalOutlined } from '@ant-design/icons';
import { LButton, LTag } from '@/shared/ui/light';
import type { RelatedEntity } from '@/shared/api/contracts/book';

export function EntityCard({ entity, sessionId }: { entity: RelatedEntity; sessionId?: string }) {
  const router = useRouter();

  const openEntity = () => {
    const query = new URLSearchParams({ entity_id: entity.entity_id });
    if (sessionId) query.set('session', sessionId);
    router.push(`/world-engine?${query.toString()}`);
  };

  const openTemporalContext = () => {
    const query = new URLSearchParams({ entity: entity.entity_id });
    if (sessionId) query.set('session', sessionId);
    router.push(`/temporal?${query.toString()}`);
  };

  return (
    <div
      style={{
        padding: '10px 12px',
        border: '1px solid #334155',
        borderRadius: 10,
        background: '#18212f',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <strong style={{ fontSize: 14, color: '#e2e8f0' }}>{entity.name}</strong>
        {entity.entity_type && (
          <LTag style={{ margin: 0, background: '#334155', color: '#93c5fd', borderColor: '#475569', fontSize: 11 }}>
            {entity.entity_type}
          </LTag>
        )}
      </div>
      {entity.description && (
        <div style={{ marginTop: 4, fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
          {entity.description.length > 180 ? `${entity.description.slice(0, 180)}…` : entity.description}
        </div>
      )}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginTop: 6 }}>
        <LButton
          type="link"
          size="small"
          icon={<GlobalOutlined />}
          onClick={openEntity}
          style={{ padding: 0, height: 'auto', fontSize: 13 }}
        >
          Открыть в World →
        </LButton>
        <LButton
          type="link"
          size="small"
          icon={<ClockCircleOutlined />}
          onClick={openTemporalContext}
          style={{ padding: 0, height: 'auto', fontSize: 13, color: '#fdba74' }}
        >
          Временной контекст →
        </LButton>
      </div>
    </div>
  );
}
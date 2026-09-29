'use client';

/**
 * /temporal?entity=... — сквозной временной контекст сущности.
 *
 * Источник данных: только существующий контракт GET /book/temporal/chain.
 * Фронт не создает связи и не показывает mock-цепочку: узлы выбираются из
 * реального массива nodes[].entity_ids. При ошибке бэкенда страница честно
 * сообщает об unavailable data.
 */

import { Suspense, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeftOutlined,
  ClockCircleOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import {
  getTemporalChain,
  getTemporalContext,
  type TemporalNode,
} from '@/shared/api/contracts/temporal';
import { ProtectedRoute } from '@/shared/lib/guards';
import {
  LAlert,
  LButton,
  LCard,
  LEmpty,
  LSpin,
  LTag,
} from '@/shared/ui/light';

const EPOCH_COLORS: Record<string, string> = {
  pre_arkaim: '#FFD700',
  satya_yuga: '#FFD700',
  treta_yuga: '#8B4513',
  dvapara_yuga: '#D2691E',
  kali_yuga: '#8B0000',
  arkaim_era: '#D2691E',
};

function formatBounds(node: TemporalNode): string {
  if (!node.bounds) return 'Границы не указаны';
  return [node.bounds.start, node.bounds.end].filter(Boolean).join(' — ') || 'Границы не указаны';
}

function TemporalContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const entityId = searchParams.get('entity') ?? '';
  const sessionId = searchParams.get('session') ?? '';
  const initialEpoch = searchParams.get('epoch') ?? '';

  const [selectedEpoch, setSelectedEpoch] = useState(initialEpoch);

  const chainQuery = useQuery({
    queryKey: ['temporal-chain'],
    queryFn: () => getTemporalChain(),
  });

  const hasExplicitEntityLinks = useMemo(
    () => Boolean(entityId && chainQuery.data?.nodes.some((node) => node.entity_ids?.includes(entityId))),
    [chainQuery.data, entityId],
  );

  // В текущем backend все entity_ids могут быть пустыми. В таком случае показываем
  // полную реальную цепочку, но не выдумываем связь выбранной сущности с эпохой.
  const visibleNodes = useMemo<TemporalNode[]>(() => {
    if (!chainQuery.data) return [];
    if (!entityId) return chainQuery.data.nodes;
    const linkedNodes = chainQuery.data.nodes.filter((node) => node.entity_ids?.includes(entityId));
    return linkedNodes.length > 0 ? linkedNodes : chainQuery.data.nodes;
  }, [chainQuery.data, entityId]);

  const contextQuery = useQuery({
    queryKey: ['temporal-context', selectedEpoch],
    queryFn: () => getTemporalContext(selectedEpoch),
    enabled: Boolean(selectedEpoch),
  });

  const backQuery = new URLSearchParams({ entity_id: entityId });
  if (sessionId) backQuery.set('session', sessionId);

  // A4: выбор эпохи отражается в URL — refresh и deep link восстанавливают контекст.
  // replace, чтобы не плодить записи в истории браузера.
  const selectEpoch = (eraId: string) => {
    setSelectedEpoch(eraId);
    const params = new URLSearchParams(searchParams.toString());
    params.set('epoch', eraId);
    router.replace(`/temporal?${params.toString()}`, { scroll: false });
  };

  const renderBody = () => {
    if (chainQuery.isLoading) {
      return (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <LSpin size="large" />
        </div>
      );
    }

    if (chainQuery.isError) {
      return (
        <LAlert
          type="error"
          showIcon
          message="Реальная временная цепочка недоступна"
          description={chainQuery.error instanceof Error ? chainQuery.error.message : 'Проверьте подключение к backend.'}
        />
      );
    }

    if (!chainQuery.data || visibleNodes.length === 0) {
      return <LEmpty description="Временная модель не содержит узлов" />;
    }

    return (
      <div style={{ display: 'grid', gap: 16 }}>
        {entityId && !hasExplicitEntityLinks && (
          <LAlert
            type="info"
            showIcon
            message="Связь сущности с конкретной эпохой в backend пока не записана"
            description="Показана полная реальная временная цепочка. Фронтенд не придумывает неподтвержденную связь."
          />
        )}
        <LCard title={<span><ClockCircleOutlined /> {hasExplicitEntityLinks ? 'Связанные эпохи' : 'Временная цепочка книги'}</span>}>
          <div style={{ display: 'grid', gap: 12 }}>
            {visibleNodes.map((node) => {
              const color = EPOCH_COLORS[node.era_id] || '#64748b';
              const isSelected = selectedEpoch === node.era_id;

              return (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => selectEpoch(node.era_id)}
                  style={{
                    display: 'grid',
                    gap: 4,
                    width: '100%',
                    textAlign: 'left',
                    padding: '12px 14px',
                    color: 'var(--foreground)',
                    background: isSelected ? 'rgba(37, 99, 235, 0.14)' : 'var(--surface-bg)',
                    border: `1px solid ${isSelected ? '#2563eb' : 'var(--card-border)'}`,
                    borderRadius: 8,
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span aria-hidden="true" style={{ color, fontSize: 18 }}>●</span>
                    <strong>{node.label}</strong>
                    {node.is_anchor && <LTag style={{ margin: 0 }}>Якорь</LTag>}
                  </div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>{node.era_id}</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>{formatBounds(node)}</div>
                </button>
              );
            })}
          </div>
        </LCard>

        {selectedEpoch ? (
          <LCard title={<span><ClockCircleOutlined /> Контекст эпохи {contextQuery.data?.epoch.name_ru || selectedEpoch}</span>}>
            {contextQuery.isLoading && (
              <div style={{ textAlign: 'center', padding: 24 }}><LSpin /></div>
            )}
            {contextQuery.isError && (
              <LAlert
                type="error"
                showIcon
                message="Контекст эпохи недоступен"
                description={contextQuery.error instanceof Error ? contextQuery.error.message : 'Проверьте подключение к backend.'}
              />
            )}
            {contextQuery.data && (
              <div style={{ display: 'grid', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <strong style={{ color: 'var(--foreground)' }}>{contextQuery.data.epoch.name_ru}</strong>
                  <LTag style={{ margin: 0 }}>{contextQuery.data.epoch.name}</LTag>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>
                    Порядок: {contextQuery.data.epoch.order}
                  </span>
                </div>
                <p style={{ color: 'var(--foreground)', lineHeight: 1.6 }}>
                  {contextQuery.data.epoch.description || 'Описание эпохи в модели не заполнено.'}
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 8 }}>
                  <LTag style={{ margin: 0, background: '#163d24', borderColor: '#237804', color: '#95de64' }}>
                    Событий: {contextQuery.data.event_count}
                  </LTag>
                  <LTag style={{ margin: 0, background: '#172554', borderColor: '#334155', color: '#93c5fd' }}>
                    Персонажей: {contextQuery.data.character_count}
                  </LTag>
                  <LTag style={{ margin: 0, background: '#451a03', borderColor: '#78350f', color: '#fdba74' }}>
                    Технологий: {contextQuery.data.technology_count}
                  </LTag>
                </div>

                {contextQuery.data.characters.length > 0 && (
                  <div>
                    <strong style={{ color: 'var(--foreground)' }}>Персонажи</strong>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
                      {contextQuery.data.characters.map((character) => (
                        <LTag key={character.id} style={{ margin: 0 }}>{character.name}</LTag>
                      ))}
                    </div>
                  </div>
                )}

                {contextQuery.data.events.length > 0 && (
                  <div>
                    <strong style={{ color: 'var(--foreground)' }}>События</strong>
                    <div style={{ display: 'grid', gap: 6, marginTop: 8 }}>
                      {contextQuery.data.events.map((event) => (
                        <div key={event.id} style={{ padding: '8px 10px', border: '1px solid var(--card-border)', borderRadius: 6 }}>
                          <strong style={{ color: 'var(--foreground)' }}>
                            {event.title_ru || event.title || event.name}
                          </strong>
                          {event.description && (
                            <div style={{ marginTop: 3, fontSize: 12, color: '#94a3b8' }}>{event.description}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </LCard>
        ) : (
          <LCard title="Контекст эпохи">
            <LEmpty description="Выберите эпоху слева, чтобы открыть реальный контекст" />
          </LCard>
        )}
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <LButton
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push(sessionId ? `/ask?session_id=${encodeURIComponent(sessionId)}` : '/ask')}
        >
          К диалогу
        </LButton>
        {entityId && (
          <LButton
            icon={<GlobalOutlined />}
            onClick={() => { window.location.href = `/world-engine?${backQuery.toString()}`; }}
          >
            Открыть в World
          </LButton>
        )}
      </div>

      <div>
        <h1 style={{ margin: '0 0 4px', fontSize: 28, color: 'var(--foreground)' }}>
          <ClockCircleOutlined /> Временной контекст
        </h1>
        <p style={{ margin: 0, color: '#94a3b8' }}>
          {entityId
            ? <>Сущность: <strong>{entityId}</strong>. Данные получены из реальной временной модели книги.</>
            : 'Реальная временная модель книги «Наследие Аркаима».'}
        </p>
      </div>

      {renderBody()}
    </div>
  );
}

export default function TemporalPage() {
  return (
    <ProtectedRoute>
      <Suspense
        fallback={
          <div style={{ textAlign: 'center', padding: 48 }}>
            <LSpin size="large" />
          </div>
        }
      >
        <TemporalContent />
      </Suspense>
    </ProtectedRoute>
  );
}
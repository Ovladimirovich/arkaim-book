'use client';

import React, { useState } from 'react';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { KnowledgeTraceCard } from '@/shared/ui/KnowledgeTraceCard';
import { getKnowledgeTrace, type KnowledgeTrace } from '@/shared/api/contracts/knowledge';
import { LCard, LInput, LButton, LSpace, LSpin, LEmpty, LTable, LTag, toast } from '@/shared/ui/light';
import { SearchOutlined, BookOutlined, EyeOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { StateView } from '@/shared/ui/StateView';

type KnowledgeEntity = {
  entity_id: string;
  name: string;
  category: string;
};

type SearchResponse = {
  query: string;
  entities: KnowledgeEntity[];
  total: number;
};

function errorDescription(error: unknown): string {
  return error instanceof Error
    ? `Сервер ответил ошибкой: ${error.message}.`
    : 'Проверьте связь с сервером и повторите попытку.';
}

function KnowledgeSearchContent() {
  const [searchQuery, setSearchQuery] = useState('');
  const [entities, setEntities] = useState<KnowledgeEntity[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const [selectedEntity, setSelectedEntity] = useState<KnowledgeEntity | null>(null);
  const [trace, setTrace] = useState<KnowledgeTrace | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceError, setTraceError] = useState<string | null>(null);

  const runSearch = async () => {
    const q = searchQuery.trim();
    if (q.length < 2) return;
    setSearchLoading(true);
    setSearchError(null);
    setSearched(true);
    try {
      const qs = new URLSearchParams({ q, limit: '20' }).toString();
      const data = await api.get<SearchResponse>(`/knowledge/cards/search?${qs}`, {});
      const found = data?.entities ?? [];
      setEntities(found);
      setTotal(typeof data?.total === 'number' ? data.total : found.length);
    } catch (e) {
      setEntities([]);
      setTotal(null);
      setSearchError(errorDescription(e));
      toast.error('Не удалось выполнить поиск по карточкам знаний');
    } finally {
      setSearchLoading(false);
    }
  };

  const handleSearch = async (entityId: string) => {
    setTrace(null);
    setTraceError(null);
    setTraceLoading(true);
    try {
      setTrace(await getKnowledgeTrace(entityId));
    } catch (e) {
      setTrace(null);
      setTraceError(errorDescription(e));
      toast.error('Не удалось загрузить трассировку знаний');
    } finally {
      setTraceLoading(false);
    }
  };

  const handleSelect = (entity: KnowledgeEntity) => {
    setSelectedEntity(entity);
    void handleSearch(entity.entity_id);
  };

  if (searchError) {
    return (
      <StateView
        state="error"
        title="Не удалось выполнить поиск по карточкам знаний"
        description={searchError}
        onRetry={() => void runSearch()}
      />
    );
  }

  const showEmpty = !searchLoading && !searchError && searched && entities.length === 0;
  const controlDisabled = searchQuery.trim().length < 2;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ marginBottom: 4 }}><BookOutlined style={{ marginRight: 8, verticalAlign: 'middle' }} />Knowledge Cards</h2>
          <span style={{ color: '#94a3b8' }}>Поиск сущностей и трассировка утверждений, доказательств и связей из книги.</span>
        </div>
      </div>

      <LCard title="Поиск сущности" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <LInput
              prefix={<SearchOutlined />}
              placeholder="Введите название сущности (например: Аркаим, Страна Городов)"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onPressEnter={() => void runSearch()}
              size="large"
            />
          </div>
          <LButton
            type="primary"
            icon={<SearchOutlined />}
            onClick={() => void runSearch()}
            disabled={controlDisabled}
          >
            Найти
          </LButton>
        </div>
        {searchLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}><LSpin size="large" /></div>
        ) : showEmpty ? (
          <LEmpty description="Сущностей не найдено. Попробуйте другой запрос." />
        ) : entities.length > 0 ? (
          <div style={{ marginTop: 12 }}>
            <p style={{ margin: '0 0 8px', color: '#666', fontSize: 12 }}>
              Найдено сущностей: <strong>{total ?? entities.length}</strong>
            </p>
            <LTable
              columns={[
                {
                  title: 'Название',
                  dataIndex: 'name',
                  key: 'name',
                  render: (name: unknown) => <strong>{String(name)}</strong>,
                },
                {
                  title: 'Категория',
                  dataIndex: 'category',
                  key: 'category',
                  render: (cat: unknown) => <LTag>{String(cat || '—')}</LTag>,
                },
                {
                  title: 'ID',
                  dataIndex: 'entity_id',
                  key: 'entity_id',
                  render: (id: unknown) => <code style={{ fontSize: 12, color: '#666' }}>{String(id)}</code>,
                },
                {
                  title: 'Действие',
                  key: 'action',
                  render: (_: unknown, record: unknown) => (
                    <LButton
                      size="small"
                      type="primary"
                      icon={<EyeOutlined />}
                      onClick={() => handleSelect(record as KnowledgeEntity)}
                    >
                      Трассировка
                    </LButton>
                  ),
                },
              ]}
              dataSource={entities}
              rowKey="entity_id"
              size="small"
              pagination={{ pageSize: 10 }}
            />
          </div>
        ) : null}
      </LCard>

      {selectedEntity && (
        <>
          <LSpace style={{ marginBottom: 16, justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <strong>Выбрана сущность:</strong>{' '}
              <span style={{ color: '#1890ff', fontWeight: 600 }}>
                {selectedEntity.name} · {selectedEntity.entity_id}
              </span>
            </div>
            <LButton onClick={() => { setSelectedEntity(null); setTrace(null); setTraceError(null); }} icon={<ClockCircleOutlined />}>
              Сбросить
            </LButton>
          </LSpace>

          {traceLoading ? (
            <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>
          ) : traceError ? (
            <StateView
              state="error"
              title="Трассировка не загружена"
              description={traceError}
              onRetry={() => void handleSearch(selectedEntity.entity_id)}
            />
          ) : (
            <KnowledgeTraceCard trace={trace ?? undefined} />
          )}
        </>
      )}
    </div>
  );
}

export function KnowledgePage() {
  return (
    <ProtectedRoute>
      <KnowledgeSearchContent />
    </ProtectedRoute>
  );
}

export default KnowledgePage;

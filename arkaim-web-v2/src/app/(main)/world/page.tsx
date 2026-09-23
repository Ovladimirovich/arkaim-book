/**
 * /world — «Модель мира» (F2_SPEC §7, reader+).
 *
 * Контракты (live-факт 2026-09-14):
 *   GET  /book/world/summary     → {summary, stats: {world_model: {total_categories, total_entities, by_category}}}
 *   GET  /book/world/categories  → {categories: {cat: count}, total}
 *   POST /book/world/search      → {world_model: entity[], relations: [], total}
 *   GET  /book/world/entity/{id} → {category, id, name, name_ru, description, properties, relations}
 *   GET  /book/world/rules       → {rules: [...]}
 *   GET  /book/world/modes       → {modes: [...]}
 *
 * Инвариант: фронт НЕ синтезирует связи — только отображает данные бэкенда.
 */
'use client';

import { App, Button, Card, Col, Input, List, Row, Skeleton, Statistic, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  ApiError,
  getWorldCategories,
  getWorldEntity,
  getWorldModes,
  getWorldRules,
  getWorldSummary,
  searchWorld,
  type WorldEntity,
  type WorldEntityDetail,
  type WorldMode,
  type WorldRule,
} from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;

const CATEGORY_COLORS: Record<string, string> = {
  philosophy: 'blue',
  language: 'green',
  geography: 'cyan',
  mythology: 'purple',
  technologies: 'orange',
  social_structure: 'gold',
  religion: 'magenta',
  rituals: 'red',
  architecture: 'volcano',
  civilizations: 'lime',
  daily_life: 'teal',
  climate: 'boron',
  transport: 'pink',
};

export default function WorldPage() {
  const { message } = App.useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEntity, setSelectedEntity] = useState<WorldEntity | null>(null);
  const [entityDetail, setEntityDetail] = useState<WorldEntityDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // ── Summary (stat card) ──
  const summary = useQuery({
    queryKey: ['world', 'summary'],
    queryFn: getWorldSummary,
    staleTime: 5 * 60_000,
  });

  // ── Categories (pie breakdown) ──
  const categories = useQuery({
    queryKey: ['world', 'categories'],
    queryFn: getWorldCategories,
    staleTime: 5 * 60_000,
  });

  // ── Rules ──
  const rules = useQuery({
    queryKey: ['world', 'rules'],
    queryFn: getWorldRules,
    staleTime: 10 * 60_000,
  });

  // ── Modes ──
  const modes = useQuery({
    queryKey: ['world', 'modes'],
    queryFn: getWorldModes,
    staleTime: 10 * 60_000,
  });

  // ── Search (on submit) ──
  const searchResults = useQuery({
    queryKey: ['world', 'search', searchQuery],
    queryFn: () => searchWorld({ query: searchQuery, limit: 20 }),
    enabled: searchQuery.length >= 2,
    staleTime: 2 * 60_000,
  });

  const handleSearch = () => {
    const q = searchQuery.trim();
    if (q.length >= 2) {
      // query auto-fires via enabled=searchQuery.length>=2 and react-query refetch
    }
  };

  const handleEntityClick = async (entity: WorldEntity) => {
    setSelectedEntity(entity);
    setEntityDetail(null);
    try {
      setDetailLoading(true);
      const detail = await getWorldEntity(entity.id);
      setEntityDetail(detail);
    } catch (e) {
      message.error(e instanceof ApiError ? e.message : 'Не удалось загрузить сущность');
    } finally {
      setDetailLoading(false);
    }
  };

  const summaryData = summary.data;
  const catsData = categories.data;
  const rulesData = rules.data;
  const modesData = modes.data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1000 }}>
      <Title level={3} style={{ margin: 0 }}>
        Модель мира
      </Title>
      <Paragraph type="secondary">
        Вычислимая модель мира книги: 547 сущностей в 13 категориях, правила консистентности и режимы исследования.
        Поиск по ключевым словам; детали сущности — по клику.
      </Paragraph>

      {/* ── Статистика мира ── */}
      <StateView
        data={summaryData}
        loading={summary.isLoading}
        error={(summary.error as ApiError | null) ?? null}
        onRetry={() => void summary.refetch()}
      >
        {(d) => (
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic title="Сущностей в мире" value={d.stats.world_model.total_entities} />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic title="Категорий" value={d.stats.world_model.total_categories} />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="Правила консистентности"
                  value={rulesData?.rules?.length ?? '—'}
                />
              </Card>
            </Col>
            <Col xs={24}>
              <Card title="Описание мира" size="small">
                <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>
                  {d.summary}
                </Paragraph>
              </Card>
            </Col>
          </Row>
        )}
      </StateView>

      {/* ── Категории ── */}
      <Card title="Категории сущностей" size="small">
        <StateView
          data={catsData}
          loading={categories.isLoading}
          error={(categories.error as ApiError | null) ?? null}
          onRetry={() => void categories.refetch()}
          empty={catsData === undefined}
        >
          {(d) => (
            <Row gutter={[8, 8]}>
              {Object.entries(d.categories).map(([cat, count]) => (
                <Col key={cat} xs={12} sm={8} md={6} lg={4}>
                  <Tag
                    color={CATEGORY_COLORS[cat] ?? 'default'}
                    style={{ fontSize: 13, padding: '4px 10px', cursor: 'pointer' }}
                    onClick={() => {
                      setSearchQuery(cat);
                      void summary.refetch();
                    }}
                  >
                    {cat} · {count}
                  </Tag>
                </Col>
              ))}
            </Row>
          )}
        </StateView>
      </Card>

      {/* ── Режимы работы ── */}
      <Card title="Режимы исследования" size="small">
        <StateView
          data={modesData}
          loading={modes.isLoading}
          error={(modes.error as ApiError | null) ?? null}
          onRetry={() => void modes.refetch()}
        >
          {(d) => (
            <Row gutter={[12, 12]}>
              {d.modes.map((m: WorldMode) => (
                <Col key={m.mode} xs={24} md={12}>
                  <Card size="small" title={m.name_ru || m.name}>
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {m.description_ru || m.description}
                    </Text>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </StateView>
      </Card>

      {/* ── Поиск ── */}
      <Card
        title="Поиск по миру"
        extra={
          searchResults.isLoading && <Text type="secondary">иск…</Text>
        }
      >
        <Input.Group compact style={{ marginBottom: 16 }}>
          <Input
            style={{ width: 'calc(100% - 100px)' }}
            placeholder="Ключевое слово: Аркаим, Кали Юга, Велик…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onPressEnter={handleSearch}
          />
          <Button type="primary" onClick={handleSearch} disabled={searchQuery.length < 2}>
            Найти
          </Button>
        </Input.Group>

        <StateView
          data={searchResults.data}
          loading={searchResults.isLoading}
          error={(searchResults.error as ApiError | null) ?? null}
          onRetry={() => void searchResults.refetch()}
          empty={searchQuery.length >= 2 && (searchResults.data?.world_model?.length ?? 0) === 0}
        >
          {(d) => (
            <>
              <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
                Найдено: {d.total} результатов
              </Paragraph>
              <List
                dataSource={d.world_model}
                renderItem={(entity) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      background: selectedEntity?.id === entity.id ? '#f0f5ff' : 'transparent',
                      borderRadius: 6,
                      padding: '8px 12px',
                    }}
                    onClick={() => void handleEntityClick(entity)}
                  >
                    <List.Item.Meta
                      title={
                        <span>
                          <Tag color={CATEGORY_COLORS[entity.category ?? ''] ?? 'default'} style={{ marginRight: 8 }}>
                            {entity.category ?? '—'}
                          </Tag>
                          {entity.name_ru || entity.name || entity.id}
                        </span>
                      }
                      description={
                        entity.description
                          ? entity.description.slice(0, 120) + (entity.description.length > 120 ? '…' : '')
                          : entity.id
                      }
                    />
                  </List.Item>
                )}
              />
            </>
          )}
        </StateView>
      </Card>

      {/* ── Детали сущности ── */}
      {selectedEntity && (
        <Card
          title={
            <span>
              <Tag color={CATEGORY_COLORS[selectedEntity.category ?? ''] ?? 'default'} style={{ marginRight: 8 }}>
                {selectedEntity.category ?? '—'}
              </Tag>
              {selectedEntity.name_ru || selectedEntity.name || selectedEntity.id}
            </span>
          }
          extra={<Button size="small" onClick={() => setSelectedEntity(null)}>Закрыть</Button>}
        >
          {detailLoading ? (
            <Skeleton active paragraph={{ rows: 3 }} />
          ) : entityDetail ? (
            <>
              {entityDetail.description && (
                <Paragraph style={{ marginBottom: 12 }}>{entityDetail.description}</Paragraph>
              )}
              {entityDetail.properties && Object.keys(entityDetail.properties).length > 0 && (
                <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>
                  Свойства:
                </Paragraph>
              )}
              {entityDetail.properties &&
                Object.entries(entityDetail.properties).map(([k, v]) => (
                  <Paragraph key={k} type="secondary" style={{ fontSize: 12, margin: 0 }}>
                    · <Text strong>{k}:</Text> {JSON.stringify(v)}
                  </Paragraph>
                ))}
              {entityDetail.relations && entityDetail.relations.length > 0 && (
                <>
                  <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 4, marginTop: 8 }}>
                    Связи ({entityDetail.relations.length}):
                  </Paragraph>
                  {entityDetail.relations.map((rel: unknown, i: number) => (
                    <Paragraph key={i} type="secondary" style={{ fontSize: 12, margin: 0 }}>
                      · {JSON.stringify(rel)}
                    </Paragraph>
                  ))}
                </>
              )}
            </>
          ) : (
            <Paragraph type="secondary">Не удалось загрузить детали</Paragraph>
          )}
        </Card>
      )}

      {/* ── Правила мира ── */}
      <Card title="Правила консистентности мира" size="small">
        <StateView
          data={rulesData}
          loading={rules.isLoading}
          error={(rules.error as ApiError | null) ?? null}
          onRetry={() => void rules.refetch()}
        >
          {(d) => (
            d.rules.length > 0 ? (
              d.rules.map((r: WorldRule) => (
                <Card key={r.id} size="small" style={{ marginBottom: 8 }}>
                  <Row align="middle" gutter={[12, 0]}>
                    <Col>
                      <Tag color={r.severity === 'hard' ? 'red' : r.severity === 'soft' ? 'orange' : 'default'}>
                        {r.severity}
                      </Tag>
                    </Col>
                    <Col>
                      <Text strong>{r.name_ru || r.name}</Text>
                      <Text type="secondary" style={{ marginLeft: 12, fontSize: 12 }}>
                        {r.description_ru || r.description}
                      </Text>
                    </Col>
                  </Row>
                </Card>
              ))
            ) : (
              <Paragraph type="secondary">Правила не заданы</Paragraph>
            )
          )}
        </StateView>
      </Card>
    </div>
  );
}

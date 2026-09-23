/**
 * /library — «Геном книги» (reader+).
 *
 * Контракты (live-факт 2026-09-15):
 *   GET /book/genome → direct BookGenome:
 *     themes: [{id, name, description, strength}] — 138 шт
 *     characters: [{id, name, aliases, type, archetype, description, strength}] — 27 шт
 *     values: [{id, name, description, strength}] — 57 шт
 *     world_entities: [{name, type, description, values, related_to}] — 7 шт
 *     author_intent: {main_message, questions_for_reader, ...}
 *     modules: dict — 11 ключей
 *
 *   GET /book/layers → direct BookLayers (5 слоёв Pulse).
 *
 * Инвариант: фронт НЕ синтезирует данные — только отображает genome и слои.
 */
'use client';

import { App, Card, Col, List, Row, Statistic, Tabs, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError, getGenome, getLayers } from '@/shared/api';
import type { BookGenome, GenomeCharacter, GenomeValue, GenomeWorldEntity } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;

const TYPE_COLORS: Record<string, string> = {
  protagonist: 'red',
  antagonist: 'volcano',
  secondary: 'blue',
  minor: 'default',
  chorus: 'cyan',
};

const ARCHETYPE_COLORS: Record<string, string> = {
  hero: 'gold',
  mentor: 'purple',
  shadow: 'red',
  trickster: 'orange',
  threshold: 'green',
};

export default function LibraryPage() {
  const { message } = App.useApp();
  const [activeTab, setActiveTab] = useState<string>('themes');

  const genome = useQuery({
    queryKey: ['library', 'genome'],
    queryFn: getGenome,
    staleTime: 10 * 60_000,
  });

  const layers = useQuery({
    queryKey: ['library', 'layers'],
    queryFn: getLayers,
    staleTime: 10 * 60_000,
  });

  const g = genome.data;
  const themes = g?.themes ?? [];
  const characters = g?.characters ?? [];
  const values = g?.values ?? [];
  const worldEntities = g?.world_entities ?? [];

  const layerKeys = ['knowledge_layer', 'meaning_layer', 'identity_layer', 'mission_layer', 'world_engine_layer'] as const;
  const layerLabels: Record<string, string> = {
    knowledge_layer: 'Слой знания',
    meaning_layer: 'Слой смысла',
    identity_layer: 'Слой идентичности',
    mission_layer: 'Слой миссии',
    world_engine_layer: 'Слой модели мира',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1000 }}>
      <Title level={3} style={{ margin: 0 }}>
        Геном книги
      </Title>
      <Paragraph type="secondary">
        Структурный каркас «Наследия Аркаима»: темы, персонажи, ценности, сущности мира,
        замысел автора и пять слоёв Pulse — живого ядра книги.
      </Paragraph>

      {/* ── Сводка ── */}
      <StateView
        data={g}
        loading={genome.isLoading}
        error={(genome.error as ApiError | null) ?? null}
        onRetry={() => void genome.refetch()}
      >
        {(d) => (
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="Тем" value={d.themes?.length ?? 0} />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="Персонажей" value={d.characters?.length ?? 0} />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="Ценностей" value={d.values?.length ?? 0} />
              </Card>
            </Col>
            <Col xs={12} sm={6}>
              <Card>
                <Statistic title="Сущностей мира" value={d.world_entities?.length ?? 0} />
              </Card>
            </Col>
          </Row>
        )}
      </StateView>

      {/* ── Табы ── */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'themes',
            label: `Темы (${themes.length})`,
            children: (
              <StateView
                data={themes.length > 0 ? themes : undefined}
                loading={genome.isLoading}
                error={(genome.error as ApiError | null) ?? null}
                onRetry={() => void genome.refetch()}
                empty={themes.length === 0}
              >
                {(items) => {
                  const sorted = [...items].sort((a, b) => (b.strength ?? 0) - (a.strength ?? 0));
                  return (
                    <List
                      dataSource={sorted}
                      renderItem={(t) => (
                        <List.Item
                          style={{
                            flexDirection: 'row',
                            justifyContent: 'space-between',
                            alignItems: 'flex-start',
                          }}
                        >
                          <List.Item.Meta
                            title={
                              <span>
                                <Tag color="blue" style={{ marginRight: 8 }}>
                                  {(t.strength ?? 0).toFixed(2)}
                                </Tag>
                                {t.name}
                              </span>
                            }
                            description={t.description || '—'}
                          />
                        </List.Item>
                      )}
                    />
                  );
                }}
              </StateView>
            ),
          },
          {
            key: 'characters',
            label: `Персонажи (${characters.length})`,
            children: (
              <StateView
                data={characters.length > 0 ? characters : undefined}
                loading={genome.isLoading}
                error={(genome.error as ApiError | null) ?? null}
                onRetry={() => void genome.refetch()}
                empty={characters.length === 0}
              >
                {(items) => (
                  <List
                    dataSource={items}
                    renderItem={(c) => (
                      <List.Item
                        style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' }}
                      >
                        <List.Item.Meta
                          title={
                            <span>
                              <Tag
                                color={TYPE_COLORS[c.type ?? ''] ?? 'default'}
                                style={{ marginRight: 8 }}
                              >
                                {c.type ?? 'unknown'}
                              </Tag>
                              {c.name}
                              {c.aliases && c.aliases.length > 0 && (
                                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                                  ({c.aliases.join(', ')})
                                </Text>
                              )}
                            </span>
                          }
                          description={
                            <>
                              {c.archetype && (
                                <Tag
                                  color={ARCHETYPE_COLORS[c.archetype] ?? 'default'}
                                  style={{ marginRight: 4 }}
                                >
                                  {c.archetype}
                                </Tag>
                              )}
                              {c.description}
                            </>
                          }
                        />
                        {c.strength !== undefined && (
                          <Tag color="green">{c.strength.toFixed(2)}</Tag>
                        )}
                      </List.Item>
                    )}
                  />
                )}
              </StateView>
            ),
          },
          {
            key: 'values',
            label: `Ценности (${values.length})`,
            children: (
              <StateView
                data={values.length > 0 ? values : undefined}
                loading={genome.isLoading}
                error={(genome.error as ApiError | null) ?? null}
                onRetry={() => void genome.refetch()}
                empty={values.length === 0}
              >
                {(items) => {
                  const sorted = [...items].sort((a, b) => (b.strength ?? 0) - (a.strength ?? 0));
                  return (
                    <List
                      dataSource={sorted}
                      renderItem={(v) => (
                        <List.Item style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                          <List.Item.Meta
                            title={v.name}
                            description={v.description || '—'}
                          />
                          <Tag color="purple">{(v.strength ?? 0).toFixed(2)}</Tag>
                        </List.Item>
                      )}
                    />
                  );
                }}
              </StateView>
            ),
          },
          {
            key: 'world-entities',
            label: `Сущности мира (${worldEntities.length})`,
            children: (
              <StateView
                data={worldEntities.length > 0 ? worldEntities : undefined}
                loading={genome.isLoading}
                error={(genome.error as ApiError | null) ?? null}
                onRetry={() => void genome.refetch()}
                empty={worldEntities.length === 0}
              >
                {(items) => (
                  <List
                    dataSource={items}
                    renderItem={(e) => (
                      <List.Item>
                        <List.Item.Meta
                          title={
                            <span>
                              <Tag color="cyan" style={{ marginRight: 8 }}>
                                {e.type ?? 'entity'}
                              </Tag>
                              {e.name ?? ''}
                            </span>
                          }
                          description={e.description || '—'}
                        />
                      </List.Item>
                    )}
                  />
                )}
              </StateView>
            ),
          },
        ]}
      />

      {/* ── Замысел автора ── */}
      {g?.author_intent && (
        <Card title="Замысел автора" size="small">
          {g.author_intent.main_message && (
            <Paragraph>
              <Text strong>Основное сообщение:</Text> {g.author_intent.main_message}
            </Paragraph>
          )}
          {g.author_intent.questions_for_reader && (
            <Paragraph>
              <Text strong>Вопросы читателю:</Text>{' '}
              {JSON.stringify(g.author_intent.questions_for_reader)}
            </Paragraph>
          )}
        </Card>
      )}

      {/* ── Слои Pulse ── */}
      <Card title="Слои Pulse — живое ядро книги" size="small">
        <StateView
          data={layers.data}
          loading={layers.isLoading}
          error={(layers.error as ApiError | null) ?? null}
          onRetry={() => void layers.refetch()}
        >
          {(d) => (
            <Row gutter={[12, 12]}>
              {layerKeys.map((key) => (
                <Col key={key} xs={24}>
                  <Card size="small" title={layerLabels[key]}>
                    <Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap', fontSize: 14 }}>
                      {d[key] || '—'}
                    </Paragraph>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </StateView>
      </Card>
    </div>
  );
}

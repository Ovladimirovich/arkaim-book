/**
 * /graph — «Граф знаний» (reader+).
 *
 * Контракты (live-факт 2026-09-15 → 2026-09-18):
 *   GET /book/graph/stats                  → direct {nodes, edges, node_types, relationship_types}
 *   GET /book/knowledge/search             → enveloped {data: [{topic, score, data:{...}}], total}
 *   GET /book/knowledge/autocomplete       → enveloped {data: [[text, type, score], ...]}
 *
 * Инвариант: фронт НЕ синтезирует связи — только отображает данные бэкенда.
 */
'use client';

import { App, Card, Col, Input, List, Row, Statistic, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { ApiError, getGraphStats, searchKnowledge, searchAutocomplete } from '@/shared/api';
import type { KnowledgeSearchResult } from '@/shared/api';
import type { AutocompleteSuggestion } from '@/shared/api/contracts/knowledge';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;

const NODE_TYPE_COLORS: Record<string, string> = {
  concept: 'blue',
  person: 'red',
  symbol: 'purple',
  civilization: 'lime',
  location: 'cyan',
  era: 'orange',
  artifact: 'gold',
};

const TYPE_FILTERS = ['all', 'expansion', 'theme', 'character', 'symbol'] as const;
const TYPE_LABELS: Record<string, string> = {
  all: 'Все',
  expansion: 'Расширения',
  theme: 'Темы',
  character: 'Персонажи',
  symbol: 'Символы',
};

export default function GraphPage() {
  App.useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<KnowledgeSearchResult[] | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeTypeFilter, setActiveTypeFilter] = useState('all');
  const [autocompleteResults, setAutocompleteResults] = useState<AutocompleteSuggestion[] | null>(null);
  const [showAutocomplete, setShowAutocomplete] = useState(false);

  const stats = useQuery({
    queryKey: ['graph', 'stats'],
    queryFn: getGraphStats,
    staleTime: 10 * 60_000,
  });

  // Autocomplete handler — debounced by input change
  const handleInputChange = async (value: string) => {
    setSearchQuery(value);
    if (value.length < 2) {
      setAutocompleteResults(null);
      setShowAutocomplete(false);
      return;
    }
    try {
      const r = await searchAutocomplete(value, 8);
      setAutocompleteResults(r.data);
      setShowAutocomplete(true);
    } catch {
      setAutocompleteResults(null);
      setShowAutocomplete(false);
    }
  };

  const handleSearch = () => {
    const q = searchQuery.trim();
    if (q.length < 2) return;
    setHasSearched(true);
    setShowAutocomplete(false);
    searchKnowledge({ q, limit: 10 })
      .then((r) => setSearchResults(r))
      .catch(() => {});
  };

  const handleSuggestionClick = (suggestion: AutocompleteSuggestion) => {
    setSearchQuery(suggestion.text);
    setShowAutocomplete(false);
    setHasSearched(false);
    setSearchResults(null);
    searchKnowledge({ q: suggestion.text, limit: 10 })
      .then((r) => {
        setSearchResults(r);
        setHasSearched(true);
      })
      .catch(() => {});
  };

  const filteredResults = activeTypeFilter === 'all'
    ? searchResults
    : searchResults?.filter((item) => {
        const d = item.data as Record<string, unknown>;
        const source = String(d?.source ?? '').toLowerCase();
        const itemType = String(d?.type ?? '').toLowerCase();
        return source.includes(activeTypeFilter) || itemType.includes(activeTypeFilter);
      });

  const nodeTypes = stats.data?.node_types ?? {};
  const relTypes = stats.data?.relationship_types ?? {};
  const sortedNodes = Object.entries(nodeTypes).sort((a, b) => b[1] - a[1]);
  const sortedRels = Object.entries(relTypes).sort((a, b) => b[1] - a[1]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1000 }}>
      <Title level={3} style={{ margin: 0 }}>
        Граф знаний
      </Title>
      <Paragraph type="secondary">
        Структурная модель знаний книги: 605 сущностей, связанных 12 отношениями.
        Поиск показывает связи темы с другими концептами.
      </Paragraph>

      {/* ── Статистика графа ── */}
      <StateView
        data={stats.data}
        loading={stats.isLoading}
        error={(stats.error as ApiError | null) ?? null}
        onRetry={() => void stats.refetch()}
      >
        {(d) => (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic title="Сущностей" value={d.nodes} />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic title="Связей" value={d.edges} />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic title="Типов узлов" value={sortedNodes.length} />
                </Card>
              </Col>
              <Col xs={12} sm={6}>
                <Card>
                  <Statistic title="Типов отношений" value={sortedRels.length} />
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Card title="Узлы по типам" size="small">
                  {sortedNodes.map(([type, count]) => (
                    <div key={type} style={{ marginBottom: 8 }}>
                      <Tag color={NODE_TYPE_COLORS[type] ?? 'default'} style={{ marginRight: 8 }}>
                        {type}
                      </Tag>
                      <Text type="secondary">{count}</Text>
                    </div>
                  ))}
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card title="Отношения по типам" size="small">
                  {sortedRels.map(([type, count]) => (
                    <div key={type} style={{ marginBottom: 8 }}>
                      <Tag color="geekblue" style={{ marginRight: 8 }}>
                        {type}
                      </Tag>
                      <Text type="secondary">{count}</Text>
                    </div>
                  ))}
                </Card>
              </Col>
            </Row>
          </>
        )}
      </StateView>

      {/* ── Поиск ── */}
      <Card title="Поиск по графу знаний" size="small">
        <div style={{ position: 'relative' }}>
          <Input.Search
            placeholder="Введите тему для поиска связей (мин. 2 символа)"
            value={searchQuery}
            onChange={(e) => void handleInputChange(e.target.value)}
            onFocus={() => { if (autocompleteResults) setShowAutocomplete(true); }}
            onBlur={() => setTimeout(() => setShowAutocomplete(false), 200)}
            onSearch={handleSearch}
            allowClear
            enterButton="Найти"
            style={{ maxWidth: 500 }}
          />

          {/* Autocomplete dropdown */}
          {showAutocomplete && autocompleteResults && autocompleteResults.length > 0 && (
            <div
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                zIndex: 1000,
                background: '#fff',
                border: '1px solid #d9d9d9',
                borderRadius: 4,
                marginTop: 4,
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                maxHeight: 240,
                overflowY: 'auto',
              }}
            >
              {autocompleteResults.map((item: AutocompleteSuggestion, i: number) => (
                <div
                  key={i}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    handleSuggestionClick(item);
                  }}
                  style={{
                    padding: '8px 12px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    borderBottom: i < autocompleteResults.length - 1 ? '1px solid #f0f0f0' : 'none',
                  }}
                >
                  <Tag
                    color={
                      item.type === 'expansion'
                        ? 'blue'
                        : item.type === 'theme'
                        ? 'purple'
                        : item.type === 'character'
                        ? 'green'
                        : 'orange'
                    }
                    style={{ fontSize: 11, flexShrink: 0 }}
                  >
                    {TYPE_LABELS[item.type] ?? item.type}
                  </Tag>
                  <Text style={{ flex: 1 }}>{item.text}</Text>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    score: {item.score}
                  </Text>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Type filter tabs */}
        {hasSearched && searchResults && searchResults.length > 0 && (
          <div style={{ marginTop: 16, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {TYPE_FILTERS.map((t) => (
              <Tag
                key={t}
                color={activeTypeFilter === t ? 'blue' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => setActiveTypeFilter(t)}
              >
                {TYPE_LABELS[t]}
              </Tag>
            ))}
          </div>
        )}

        {hasSearched && searchResults === null && (
          <Paragraph type="secondary" style={{ marginTop: 16 }}>
            Ничего не найдено
          </Paragraph>
        )}

        {filteredResults && filteredResults.length > 0 && (
          <List
            style={{ marginTop: 16 }}
            dataSource={filteredResults}
            renderItem={(item) => (
              <List.Item
                style={{
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  gap: 8,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
                  <Tag color="blue">{item.topic}</Tag>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    relevance: {(item.score ?? 0).toFixed(1)}
                  </Text>
                </div>
                <Paragraph
                  type="secondary"
                  style={{ margin: 0, fontSize: 13, width: '100%' }}
                >
                  {(item.data as Record<string, unknown>).content as string | undefined || '—'}
                </Paragraph>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, width: '100%' }}>
                  {Array.isArray((item.data as Record<string, unknown>).graph_links) &&
                    ((item.data as Record<string, unknown>).graph_links as string[]).map((link) => (
                      <Tag key={link} color="purple">
                        → {link}
                      </Tag>
                    ))}
                  {Array.isArray((item.data as Record<string, unknown>).cross_references) &&
                    ((item.data as Record<string, unknown>).cross_references as string[]).map((ref) => (
                      <Tag key={ref} color="cyan">
                        ↔ {ref}
                      </Tag>
                    ))}
                </div>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}

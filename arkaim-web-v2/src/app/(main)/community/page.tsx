/**
 * /community — Сообщество (reader+).
 *
 * Использует только существующие backend endpoints без изменений:
 *   GET /book/community/timeline       — хроника событий книги
 *   GET /book/community/interpretations/stats — статистика интерпретаций
 *   GET /book/community/artifacts/stats — статистика артефактов
 *   GET /book/community/knowledge/status — статус модулей знаний
 *   GET /book/community/search?q=      — поиск по интерпретациям и артефактам
 */
'use client';

import { useState } from 'react';
import {
  App,
  Card,
  Col,
  Input,
  Row,
  Statistic,
  Tag,
  Timeline,
  Typography,
} from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  getCommunityTimeline,
  getInterpretationsStats,
  getArtifactsStats,
  getKnowledgeStatus,
  searchCommunity,
  type CommunityEvent,
} from '@/shared/api';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text, Paragraph } = Typography;

// ── Constants ──────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  civilization: 'gold',
  city: 'blue',
  migration: 'purple',
  event: 'default',
};

const TYPE_LABELS: Record<string, string> = {
  civilization: 'Цивилизация',
  city: 'Город',
  migration: 'Миграция',
  event: 'Событие',
};

const ALL_TYPES = ['all', 'civilization', 'city', 'migration', 'event'];

// ── Page ───────────────────────────────────────────────────

export default function CommunityPage() {
  const { message: msgApi } = App.useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{ interpretations: unknown[]; artifacts: unknown[]; total: number } | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all');
  const [debounceTimer, setDebounceTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  const timeline = useQuery({
    queryKey: ['community', 'timeline'],
    queryFn: getCommunityTimeline,
    staleTime: 5 * 60_000,
  });

  const interpStats = useQuery({
    queryKey: ['community', 'interpStats'],
    queryFn: getInterpretationsStats,
    staleTime: 5 * 60_000,
  });

  const artifactStats = useQuery({
    queryKey: ['community', 'artifactStats'],
    queryFn: getArtifactsStats,
    staleTime: 5 * 60_000,
  });

  const knowledgeStatus = useQuery({
    queryKey: ['community', 'knowledgeStatus'],
    queryFn: getKnowledgeStatus,
    staleTime: 5 * 60_000,
  });

  const handleSearch = () => {
    const q = searchQuery.trim();
    if (q.length < 2) return;
    setHasSearched(true);
    searchCommunity(q)
      .then((r) => setSearchResults(r))
      .catch(() => {
        msgApi.error('Ошибка поиска');
        setHasSearched(false);
      });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchQuery(value);
    if (debounceTimer) clearTimeout(debounceTimer);
    const timer = setTimeout(() => {
      if (value.trim().length >= 2) handleSearch();
    }, 300);
    setDebounceTimer(timer);
  };

  const filteredEvents =
    activeFilter === 'all'
      ? timeline.data?.events ?? []
      : (timeline.data?.events ?? []).filter((e: CommunityEvent) => e.type === activeFilter);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        Сообщество
      </Title>
      <Paragraph type="secondary">
        Хроника событий Аркаима, интерпретации читателей и поиск по знаниям.
      </Paragraph>

      {/* ── Stats ── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <StateView
              data={interpStats.data}
              loading={interpStats.isLoading}
              error={(interpStats.error as ApiError | null) ?? null}
              onRetry={() => void interpStats.refetch()}
            >
              {(d) => (
                <Statistic
                  title="Интерпретаций"
                  value={d.total}
                  suffix={
                    d.pending > 0 ? (
                      <Tag color="orange">{d.pending} на модерации</Tag>
                    ) : undefined
                  }
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8}>
          <Card>
            <StateView
              data={artifactStats.data}
              loading={artifactStats.isLoading}
              error={(artifactStats.error as ApiError | null) ?? null}
              onRetry={() => void artifactStats.refetch()}
            >
              {(d) => (
                <Statistic
                  title="Артефактов"
                  value={d.total}
                  suffix={
                    d.pending > 0 ? (
                      <Tag color="orange">{d.pending} на модерации</Tag>
                    ) : undefined
                  }
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={8}>
          <Card>
            <StateView
              data={knowledgeStatus.data}
              loading={knowledgeStatus.isLoading}
              error={(knowledgeStatus.error as ApiError | null) ?? null}
              onRetry={() => void knowledgeStatus.refetch()}
            >
              {(d) => (
                <Statistic
                  title="Модулей знаний"
                  value={d.module_count}
                  suffix={<Tag color="blue">expansion</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>
      </Row>

      {/* ── Timeline ── */}
      <Card
        title="Хроника Аркаима"
        extra={
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {ALL_TYPES.map((t) => (
              <Tag
                key={t}
                color={activeFilter === t ? 'blue' : 'default'}
                style={{ cursor: 'pointer' }}
                onClick={() => setActiveFilter(t)}
              >
                {t === 'all' ? 'Все' : TYPE_LABELS[t] ?? t}
              </Tag>
            ))}
          </div>
        }
      >
        <StateView
          data={timeline.data}
          loading={timeline.isLoading}
          error={(timeline.error as ApiError | null) ?? null}
          onRetry={() => void timeline.refetch()}
          empty={filteredEvents.length === 0}
        >
          {() => (
            <Timeline
              items={filteredEvents.map((evt: CommunityEvent) => ({
                color: TYPE_COLORS[evt.type] ?? 'blue',
                children: (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Tag color={TYPE_COLORS[evt.type] ?? 'blue'} style={{ fontSize: 11 }}>
                        {TYPE_LABELS[evt.type] ?? evt.type}
                      </Tag>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {evt.year}
                      </Text>
                    </div>
                    <div style={{ marginTop: 4 }}>{evt.title}</div>
                  </div>
                ),
              }))}
            />
          )}
        </StateView>
      </Card>

      {/* ── Search ── */}
      <Card title="Поиск по сообществу" size="small">
        <Input.Search
          placeholder="Искать интерпретации и артефакты..."
          value={searchQuery}
          onChange={handleChange}
          onSearch={handleSearch}
          onPressEnter={handleSearch}
          allowClear
          enterButton={<><SearchOutlined /> Найти</>}
          style={{ maxWidth: 480 }}
        />

        {hasSearched && searchResults === null && (
          <Paragraph type="secondary" style={{ marginTop: 16 }}>
            Ничего не найдено
          </Paragraph>
        )}

        {searchResults !== null && searchResults.total === 0 && hasSearched && (
          <Paragraph type="secondary" style={{ marginTop: 16 }}>
            По запросу «{searchQuery}» ничего не найдено. Будьте первым — создайте интерпретацию!
          </Paragraph>
        )}

        {searchResults !== null && searchResults.total > 0 && (
          <div style={{ marginTop: 16 }}>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Найдено: {searchResults.total}
            </Text>
            {searchResults.interpretations.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Text strong>Интерпретации</Text>
                {searchResults.interpretations.slice(0, 5).map((item: unknown, i: number) => {
                  const r = item as Record<string, unknown>;
                  return (
                    <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                      <Text style={{ fontSize: 13 }}>
                        {String(r.text ?? '').slice(0, 120)}
                      </Text>
                      {Array.isArray(r.themes) && (r.themes as string[]).length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          {(r.themes as string[]).slice(0, 3).map((t) => (
                            <Tag key={t} style={{ fontSize: 11, marginRight: 4 }}>
                              {t}
                            </Tag>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            {searchResults.artifacts.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Text strong>Артефакты</Text>
                {searchResults.artifacts.slice(0, 5).map((item: unknown, i: number) => {
                  const r = item as Record<string, unknown>;
                  return (
                    <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                      <Text strong style={{ fontSize: 13 }}>
                        {String(r.title ?? '')}
                      </Text>
                      <div style={{ marginTop: 4 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {String(r.description ?? '').slice(0, 120)}
                        </Text>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

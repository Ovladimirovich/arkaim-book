/**
 * /analytics — сводная аналитика книги (MVP).
 *
 * Использует только существующие backend endpoints без изменений:
 *   GET /book/reader/history/stats  — questions, sessions текущего читателя
 *   GET /book/reader/reading-progress — прогресс чтения
 *   GET /book/graph/stats           — узлы и связи графа знаний
 *   GET /book/world/summary         — сущности мира по категориям
 *   GET /book/cache/stats           — статистика кэшей
 *   GET /book/os/documents          — количество загруженных документов
 */
'use client';

import { Card, Col, Row, Statistic, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import {
  getReaderHistoryStats,
  getReadingProgress,
} from '@/shared/api/contracts/reader';
import { getGraphStats } from '@/shared/api/contracts/knowledge';
import { getWorldSummary, type WorldSummary } from '@/shared/api/contracts/world';
import { getCacheStats, type CacheStats, listDocuments, type Document } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text } = Typography;

// ── Helper ────────────────────────────────────────────────

function fmtTime(seconds: number): string {
  if (seconds < 60) return `${seconds} сек`;
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} мин`;
  const h = Math.floor(m / 60);
  return `${h} ч ${m % 60} мин`;
}

// ── Page ───────────────────────────────────────────────────

export default function AnalyticsPage() {
  const historyStats = useQuery({
    queryKey: ['analytics', 'historyStats'],
    queryFn: getReaderHistoryStats,
    staleTime: 60_000,
  });

  const progress = useQuery({
    queryKey: ['analytics', 'progress'],
    queryFn: getReadingProgress,
    staleTime: 60_000,
  });

  const graphStats = useQuery({
    queryKey: ['analytics', 'graphStats'],
    queryFn: getGraphStats,
    staleTime: 120_000,
  });

  const worldSummary = useQuery({
    queryKey: ['analytics', 'worldSummary'],
    queryFn: getWorldSummary,
    staleTime: 120_000,
  });

  const cacheStats = useQuery({
    queryKey: ['analytics', 'cacheStats'],
    queryFn: getCacheStats,
    staleTime: 120_000,
  });

  const documents = useQuery({
    queryKey: ['analytics', 'documents'],
    queryFn: () => listDocuments(),
    staleTime: 120_000,
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        Аналитика
      </Title>

      {/* ── StatCards ── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={historyStats.data}
              loading={historyStats.isLoading}
              error={(historyStats.error as ApiError | null) ?? null}
              onRetry={() => void historyStats.refetch()}
            >
              {(d) => (
                <Statistic
                  title="Вопросов книге"
                  value={d.questions}
                  suffix={<Tag color="blue">вы ваш</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={graphStats.data}
              loading={graphStats.isLoading}
              error={(graphStats.error as ApiError | null) ?? null}
              onRetry={() => void graphStats.refetch()}
            >
              {(d) => (
                <Statistic
                  title="Сущностей в графе"
                  value={d.nodes}
                  suffix={<Tag color="green">{d.edges} связей</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={worldSummary.data}
              loading={worldSummary.isLoading}
              error={(worldSummary.error as ApiError | null) ?? null}
              onRetry={() => void worldSummary.refetch()}
            >
              {(d) => (
                <Statistic
                  title="Сущностей мира"
                  value={d.stats?.world_model?.total_entities ?? 0}
                  suffix={
                    <Tag color="purple">
                      {d.stats?.world_model?.total_categories ?? 0} категорий
                    </Tag>
                  }
                />
              )}
            </StateView>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <StateView
              data={documents.data}
              loading={documents.isLoading}
              error={(documents.error as ApiError | null) ?? null}
              onRetry={() => void documents.refetch()}
              empty={documents.data?.length === 0}
            >
              {(d: Document[]) => (
                <Statistic
                  title="Документов BookOS"
                  value={d.length}
                  suffix={<Tag color="orange">загружено</Tag>}
                />
              )}
            </StateView>
          </Card>
        </Col>
      </Row>

      {/* ── Reading Progress ── */}
      <Card title="Прогресс чтения" size="small">
        <StateView
          data={progress.data}
          loading={progress.isLoading}
          error={(progress.error as ApiError | null) ?? null}
          onRetry={() => void progress.refetch()}
          empty={!progress.data?.stats}
        >
          {(d) => {
            const stats = d.stats;
            return (
              <Row gutter={[16, 16]}>
                <Col xs={8}>
                  <Statistic
                    title="Глав начато"
                    value={stats.chapters_started}
                  />
                </Col>
                <Col xs={8}>
                  <Statistic
                    title="Глав прочитано"
                    value={stats.chapters_completed}
                  />
                </Col>
                <Col xs={8}>
                  <Statistic
                    title="Времени за книгой"
                    value={fmtTime(stats.total_seconds)}
                  />
                </Col>
              </Row>
            );
          }}
        </StateView>
      </Card>

      {/* ── World Categories ── */}
      <Card title="Категории мира" size="small">
        <StateView
          data={worldSummary.data}
          loading={worldSummary.isLoading}
          error={(worldSummary.error as ApiError | null) ?? null}
          onRetry={() => void worldSummary.refetch()}
        >
          {(d: WorldSummary) => {
            const byCat = d.stats?.world_model?.by_category ?? {};
            const entries = Object.entries(byCat).sort((a, b) => b[1] - a[1]);
            const maxCount = entries[0]?.[1] ?? 1;
            return (
              <Row gutter={[12, 12]}>
                {entries.map(([cat, count]) => (
                  <Col key={cat} xs={24} sm={12} md={8} lg={6}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        padding: '8px 12px',
                        background: 'var(--reading-surface, #fafafa)',
                        borderRadius: 6,
                        border: '1px solid var(--reading-border, #f0f0f0)',
                      }}
                    >
                      <div
                        style={{
                          flex: 1,
                          height: 6,
                          background: 'var(--reading-border, #f0f0f0)',
                          borderRadius: 3,
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${(count / maxCount) * 100}%`,
                            height: '100%',
                            background: 'var(--reading-accent, #1677ff)',
                            borderRadius: 3,
                          }}
                        />
                      </div>
                      <Text style={{ fontSize: 12, color: 'var(--reading-text-secondary, #888)' }}>
                        {count}
                      </Text>
                      <Text style={{ fontSize: 12 }}>
                        {cat.replace(/_/g, ' ')}
                      </Text>
                    </div>
                  </Col>
                ))}
              </Row>
            );
          }}
        </StateView>
      </Card>

      {/* ── Cache Stats ── */}
      <Card title="Статистика кэшей" size="small">
        <StateView
          data={cacheStats.data}
          loading={cacheStats.isLoading}
          error={(cacheStats.error as ApiError | null) ?? null}
          onRetry={() => void cacheStats.refetch()}
        >
          {(d: CacheStats) => (
            <Row gutter={[12, 12]}>
              {Object.entries(d).map(([name, s]) => (
                <Col key={name} xs={24} sm={12} md={8}>
                  <Card size="small" title={name}>
                    <Statistic
                      title="Hits"
                      value={s.hits}
                      valueStyle={{ fontSize: 16 }}
                    />
                    <Statistic
                      title="Misses"
                      value={s.misses}
                      valueStyle={{ fontSize: 16, color: '#cf1322' }}
                    />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      hit rate: {s.hit_rate}
                    </Text>
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

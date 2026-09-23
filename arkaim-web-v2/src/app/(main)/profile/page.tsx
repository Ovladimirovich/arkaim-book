/**
 * /profile — профиль читателя (F2_SPEC §1).
 *
 * Контракты (live-факт F2-шаг 0):
 *   GET /book/reader/profile → {reader_id, display_name, questions_total,
 *     conversation_count, last_topic, topics: [{name, depth, questions}]}
 *   GET /book/reader/history → conversations-контракт (для /book/ask-пользователя
 *     пуст — это архитектура backend, красная линия F2; см. contracts/reader.ts)
 *   GET /book/reader/reading-progress → {data, stats} — статистика чтения.
 */
'use client';

import { Card, Col, List, Row, Statistic, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import {
  getReaderProfile,
  getReaderHistory,
  getReadingProgress,
  ApiError,
} from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph } = Typography;

export default function ProfilePage() {
  const profile = useQuery({
    queryKey: ['reader', 'profile'],
    queryFn: () => getReaderProfile(),
    staleTime: 60_000,
  });

  const history = useQuery({
    queryKey: ['reader', 'history'],
    queryFn: () => getReaderHistory(20),
    staleTime: 60_000,
  });

  const progress = useQuery({
    queryKey: ['reader', 'progress'],
    queryFn: () => getReadingProgress(),
    staleTime: 60_000,
  });

  const p = profile.data;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      <Title level={3} style={{ margin: 0 }}>
        Профиль читателя
      </Title>

      <StateView
        data={p}
        loading={profile.isLoading}
        error={(profile.error as ApiError | null) ?? null}
        onRetry={() => void profile.refetch()}
      >
        {(d) => (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="Вопросов книге" value={d.questions_total} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic title="Диалогов" value={d.conversation_count} />
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card>
                  <Statistic
                    title="Глав начато"
                    value={progress.data?.stats.chapters_started ?? 0}
                  />
                </Card>
              </Col>
            </Row>

            <Card title="О вас" size="small">
              <Paragraph style={{ marginBottom: 4 }}>
                Имя: <strong>{d.display_name || '—'}</strong>
                <Tag style={{ marginInlineStart: 8 }}>reader_id: {d.reader_id.slice(0, 8)}…</Tag>
              </Paragraph>
              {d.last_topic && (
                <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                  Последняя тема: {d.last_topic}
                </Paragraph>
              )}
            </Card>

            <Card title="Темы (память книги о вас)" size="small">
              {d.topics && d.topics.length > 0 ? (
                <List
                  size="small"
                  dataSource={d.topics}
                  renderItem={(t) => (
                    <List.Item>
                      <List.Item.Meta
                        title={t.name}
                        description={`глубина ${t.depth.toFixed(2)} · вопросов: ${t.questions}`}
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                  Пока пусто: задайте первый вопрос на главной — книга начнёт запоминать
                  ваши темы.
                </Paragraph>
              )}
            </Card>
          </>
        )}
      </StateView>

      <Card title="История вопросов" size="small">
        <StateView
          data={history.data}
          loading={history.isLoading}
          error={(history.error as ApiError | null) ?? null}
          onRetry={() => void history.refetch()}
          empty={(history.data?.length ?? 0) === 0}
        >
          {(items) => (
            <List
              size="small"
              dataSource={items.slice(0, 20)}
              renderItem={(h) => (
                <List.Item>
                  <List.Item.Meta
                    title={h.content.slice(0, 120)}
                    description={new Date(h.created_at).toLocaleString('ru-RU')}
                  />
                </List.Item>
              )}
            />
          )}
        </StateView>
        {(history.data?.length ?? 0) === 0 && !history.isLoading && !history.error && (
          <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 12 }}>
            История диалогов с /v1-чатом появится здесь; вопросы через «Спросить книгу»
            книга хранит в темах профиля (см. выше).
          </Paragraph>
        )}
      </Card>

      {progress.data && progress.data.stats && (
        <Card title="Чтение" size="small">
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="Глав начато"
                value={progress.data.stats.chapters_started}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Глав прочитано"
                value={progress.data.stats.chapters_completed}
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="Времени за книгой"
                value={Math.round(progress.data.stats.total_seconds / 60)}
                suffix="мин"
              />
            </Col>
          </Row>
        </Card>
      )}
    </div>
  );
}

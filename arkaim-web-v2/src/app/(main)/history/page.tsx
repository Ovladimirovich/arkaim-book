/**
 * /history — история сессий читателя (F5).
 *
 * Контракты:
 *   GET /book/reader/history/sessions → enveloped ReaderSessionItem[]
 *   GET /book/reader/history/full?limit=N&session_id=X → enveloped ReaderHistoryFullItem[]
 *
 * Backend constraints:
 *   - sessions: no query params (list all sessions)
 *   - full: limit (default 100), session_id (optional)
 *   - date range / search: client-side filter only
 */
'use client';

import { useState, useMemo } from 'react';
import { Card, Col, Input, Row, Select, Statistic, Typography, List, Tag, Space } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getReaderHistorySessions, getReaderHistoryFull } from '@/shared/api/contracts/reader';
import { ApiError } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Text } = Typography;

// ── Helpers ───────────────────────────────────────────────

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    });
  } catch {
    return iso;
  }
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

// ── Page ──────────────────────────────────────────────────

export default function HistoryPage() {
  const [search, setSearch] = useState('');
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [limit, setLimit] = useState(100);

  const sessions = useQuery({
    queryKey: ['history', 'sessions'],
    queryFn: getReaderHistorySessions,
    staleTime: 60_000,
  });

  const historyFull = useQuery({
    queryKey: ['history', 'full', selectedSession, limit],
    queryFn: () => getReaderHistoryFull({ limit, session_id: selectedSession }),
    enabled: !!selectedSession,
    staleTime: 30_000,
  });

  // Client-side filters
  const filteredHistory = useMemo(() => {
    if (!historyFull.data) return [];
    if (!search) return historyFull.data;
    const q = search.toLowerCase();
    return historyFull.data.filter((item) => item.content.toLowerCase().includes(q));
  }, [historyFull.data, search]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <Title level={3} style={{ margin: 0 }}>
        История сессий
      </Title>

      <Row gutter={[16, 16]}>
        {/* ── Sessions list ── */}
        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <span>Сессии</span>
                <Tag>{sessions.data?.length ?? 0}</Tag>
              </Space>
            }
            size="small"
            bodyStyle={{ maxHeight: 500, overflowY: 'auto' }}
          >
            <StateView
              data={sessions.data}
              loading={sessions.isLoading}
              error={(sessions.error as ApiError | null) ?? null}
              onRetry={() => void sessions.refetch()}
            >
              {(items) => (
                <List
                  size="small"
                  dataSource={items}
                  renderItem={(s) => (
                    <List.Item
                      onClick={() => setSelectedSession(s.session_id)}
                      style={{
                        cursor: 'pointer',
                        background: selectedSession === s.session_id ? '#f0f5ff' : 'transparent',
                        borderRadius: 4,
                        padding: '8px 12px',
                      }}
                    >
                      <Space direction="vertical" size={0} style={{ width: '100%' }}>
                        <Space>
                          <Text strong style={{ fontSize: 13 }}>
                            {fmtDate(s.created_at)}
                          </Text>
                          <Tag color="blue">{s.question_count} вопросов</Tag>
                        </Space>
                        {s.last_question_at && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            Последний: {fmtTime(s.last_question_at)}
                          </Text>
                        )}
                      </Space>
                    </List.Item>
                  )}
                />
              )}
            </StateView>
            {(sessions.data?.length ?? 0) === 0 && !sessions.isLoading && !sessions.error && (
              <Text type="secondary" style={{ fontSize: 13 }}>
                Нет сессий
              </Text>
            )}
          </Card>
        </Col>

        {/* ── History content ── */}
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <span>Контент сессии</span>
                {selectedSession && (
                  <Tag color="geekblue">{selectedSession.slice(0, 12)}…</Tag>
                )}
              </Space>
            }
            extra={
              <Space>
                <Select
                  value={limit}
                  onChange={setLimit}
                  size="small"
                  style={{ width: 80 }}
                  options={[
                    { value: 20, label: '20' },
                    { value: 50, label: '50' },
                    { value: 100, label: '100' },
                  ]}
                />
                <Input.Search
                  placeholder="Поиск…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  size="small"
                  style={{ width: 200 }}
                  allowClear
                />
              </Space>
            }
            size="small"
          >
            {!selectedSession ? (
              <Text type="secondary" style={{ fontSize: 13 }}>
                Выберите сессию слева для просмотра контента
              </Text>
            ) : (
              <>
                <StateView
                  data={historyFull.data}
                  loading={historyFull.isLoading}
                  error={(historyFull.error as ApiError | null) ?? null}
                  onRetry={() => void historyFull.refetch()}
                >
                  {(items) => (
                    <>
                      <div style={{ marginBottom: 12 }}>
                        <Statistic
                          title="Показано вопросов"
                          value={filteredHistory.length}
                          suffix={`/ ${items.length}`}
                          style={{ fontSize: 13 }}
                        />
                      </div>
                      <List
                        size="small"
                        dataSource={filteredHistory}
                        renderItem={(item) => (
                          <List.Item>
                            <Space direction="vertical" size={2} style={{ width: '100%' }}>
                              <Text type="secondary" style={{ fontSize: 11 }}>
                                {fmtDate(item.created_at)} {fmtTime(item.created_at)}
                              </Text>
                              <Text style={{ fontSize: 13 }}>{item.content}</Text>
                            </Space>
                          </List.Item>
                        )}
                      />
                    </>
                  )}
                </StateView>
              </>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

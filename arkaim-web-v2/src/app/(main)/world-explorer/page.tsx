/**
 * /world-explorer — «Исследование мира» (World Explorer).
 *
 * Контракты (live-факт 2026-09-14, backend narrative_engine/api_routes.py):
 *   POST /book/world-explorer/explore              → ExplorationResult
 *   POST /book/world-explorer/validate             → CompatibilityResult
 *   GET  /book/world-explorer/epochs               → Epoch[]
 *   GET  /book/world-explorer/stats                → WorldExplorerStats
 *   GET  /book/world-explorer/hypotheses/{epoch}   → Hypothesis[]
 *   GET  /book/world-explorer/possibilities/{epoch}→ Possibility[]
 *   GET/POST/DELETE /book/world-explorer/history   → история (сохраняется после исследования)
 *   POST /book/world-explorer/feedback             → отзыв к ветви
 *   POST /book/world-explorer/generate-from-branch → промпт для LLM по ветви
 *
 * Инвариант: фронт НЕ вычисляет ветви сам — только отображает данные бэкенда.
 */
'use client';

import { useMemo, useState } from 'react';
import {
  Alert,
  App,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Input,
  InputNumber,
  Modal,
  Progress,
  Rate,
  Row,
  Select,
  Space,
  Statistic,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  deleteExploration,
  exploreFromHypothesis,
  exploreWorld,
  generateFromBranch,
  getExplorationDetail,
  getExplorationHistory,
  getExplorerEpochs,
  getExplorerStats,
  getHypotheses,
  getPossibilities,
  saveExploration,
  submitFeedback,
  validateIdea,
  type CompatibilityResult,
  type Epoch,
  type ExplorationResult,
  type HistoryItem,
  type Hypothesis,
  type Possibility,
  type RankedBranch,
} from '@/shared/api';

const { Title, Paragraph, Text } = Typography;

const BRANCH_TYPE_LABELS: Record<string, string> = {
  conservative: 'Консервативное',
  moderate: 'Умеренное',
  radical: 'Радикальное',
  unexpected: 'Неожиданное',
};
const RISK_COLORS: Record<string, string> = {
  low: '#52c41a',
  medium: '#faad14',
  high: '#ff7a45',
  rejected: '#ff4d4f',
};
const CRITERIA_LABELS: Record<string, string> = {
  canon_alignment: 'Канон',
  logical_consistency: 'Логика',
  thematic_depth: 'Глубина',
  dramatic_potential: 'Драма',
  originality: 'Оригинал',
};

const pct = (v: number) => Math.round(v * 100);
const scoreColor = (v: number) => (v >= 0.8 ? '#52c41a' : v >= 0.6 ? '#faad14' : '#ff4d4f');

function BranchTypeTag({ type }: { type: string }) {
  const label = BRANCH_TYPE_LABELS[type] ?? type;
  const color =
    type === 'unexpected' ? 'purple' : type === 'radical' ? 'orange' : type === 'moderate' ? 'green' : 'blue';
  return <Tag color={color}>{label}</Tag>;
}

export default function WorldExplorerPage() {
  const { message } = App.useApp();

  const [prompt, setPrompt] = useState('');
  const [epoch, setEpoch] = useState<string | undefined>();
  const [branchCount, setBranchCount] = useState(3);
  const [result, setResult] = useState<ExplorationResult | null>(null);
  const [compatibility, setCompatibility] = useState<CompatibilityResult | null>(null);

  const [selectedBranch, setSelectedBranch] = useState<RankedBranch | null>(null);
  const [feedbackRating, setFeedbackRating] = useState(0);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [generatedText, setGeneratedText] = useState<{ system_instruction: string; user_prompt: string } | null>(
    null,
  );
  const [activeTab, setActiveTab] = useState('explore');

  // ── Справочники ──
  const epochsQuery = useQuery({ queryKey: ['we', 'epochs'], queryFn: getExplorerEpochs, staleTime: 10 * 60_000 });
  const statsQuery = useQuery({ queryKey: ['we', 'stats'], queryFn: getExplorerStats, staleTime: 10 * 60_000 });

  const epochs: Epoch[] = useMemo(() => epochsQuery.data ?? [], [epochsQuery.data]);
  const epochOptions = useMemo(() => epochs.map((e) => ({ value: e.id, label: e.name_ru })), [epochs]);

  // ── Проверка совместимости ──
  const validateMutation = useMutation({
    mutationFn: () => validateIdea({ prompt, epoch }),
    onSuccess: (data) => setCompatibility(data),
    onError: () => setCompatibility(null),
  });

  // ── Исследование ──
  const exploreMutation = useMutation({
    mutationFn: () => exploreWorld({ prompt, epoch, branch_count: branchCount }),
    onSuccess: (data) => {
      setResult(data);
      setActiveTab('explore');
      // Сохраняем в историю «в фоне» — ошибка сохранения не ломает UX.
      void saveExploration({
        prompt,
        epoch: epoch ?? null,
        branch_count: branchCount,
        hypothesis_id: data.hypothesis?.id ?? null,
        hypothesis_title: data.hypothesis?.title ?? null,
        result_json: JSON.stringify(data),
        summary: data.summary,
        overall_score: data.ranked_branches[0]?.quality_score ?? 0,
        branch_count_actual: data.ranked_branches.length,
        duration_ms: data.duration_ms,
      }).catch(() => undefined);
    },
    onError: (e) => message.error(e instanceof Error ? e.message : 'Не удалось выполнить исследование'),
  });

  const canExplore = prompt.trim().length >= 5 && !exploreMutation.isPending;

  // ── Детали ветви: отзыв + генерация текста ──
  const feedbackMutation = useMutation({
    mutationFn: () =>
      submitFeedback({
        branch_rank: selectedBranch?.rank ?? 0,
        branch_type: selectedBranch?.branch_type ?? '',
        branch_title: selectedBranch?.title ?? '',
        rating: feedbackRating,
        comment: feedbackComment,
      }),
    onSuccess: () => {
      message.success('Отзыв сохранён');
      setFeedbackRating(0);
      setFeedbackComment('');
    },
    onError: (e) => message.error(e instanceof Error ? e.message : 'Не удалось сохранить отзыв'),
  });

  const genMutation = useMutation({
    mutationFn: () =>
      generateFromBranch({
        exploration_prompt: prompt,
        branch_title: selectedBranch?.title ?? '',
        branch_type: selectedBranch?.branch_type ?? '',
        epoch,
        quality_score: selectedBranch?.quality_score,
        strengths: selectedBranch?.strengths ?? [],
        weaknesses: selectedBranch?.weaknesses ?? [],
      }),
    onSuccess: (data) => setGeneratedText({ system_instruction: data.system_instruction, user_prompt: data.user_prompt }),
    onError: (e) => message.error(e instanceof Error ? e.message : 'Не удалось сгенерировать текст'),
  });

  const closeModal = () => {
    setSelectedBranch(null);
    setGeneratedText(null);
    setFeedbackRating(0);
    setFeedbackComment('');
  };

  // ── Вкладка «Гипотезы» ──
  const hypQuery = useQuery({
    queryKey: ['we', 'hypotheses', epoch],
    queryFn: () => getHypotheses(epoch ?? 'satya_yuga'),
    enabled: activeTab === 'hypotheses' && !!epoch,
    staleTime: 5 * 60_000,
  });
  const hypExplore = useMutation({
    mutationFn: ({ id, ep }: { id: string; ep: string }) => exploreFromHypothesis(id, ep, branchCount),
    onSuccess: (data) => {
      setResult(data);
      setActiveTab('explore');
      message.success('Исследование по гипотезе готово');
    },
    onError: (e) => message.error(e instanceof Error ? e.message : 'Ошибка исследования гипотезы'),
  });

  // ── Вкладка «Возможности» ──
  const possQuery = useQuery({
    queryKey: ['we', 'possibilities', epoch],
    queryFn: () => getPossibilities(epoch ?? 'satya_yuga'),
    enabled: activeTab === 'possibilities' && !!epoch,
    staleTime: 5 * 60_000,
  });

  // ── Вкладка «История» ──
  const historyQuery = useQuery({
    queryKey: ['we', 'history'],
    queryFn: () => getExplorationHistory(50),
    enabled: activeTab === 'history',
    staleTime: 30_000,
  });
  const deleteHist = useMutation({
    mutationFn: (id: number) => deleteExploration(id),
    onSuccess: () => {
      message.success('Запись удалена');
      void historyQuery.refetch();
    },
    onError: (e) => message.error(e instanceof Error ? e.message : 'Не удалось удалить запись'),
  });
  const openFromHistory = async (id: number) => {
    try {
      const item = await getExplorationDetail(id);
      if (item.result) {
        setPrompt(item.prompt);
        if (item.epoch) setEpoch(item.epoch);
        setResult(item.result);
        setActiveTab('explore');
      } else {
        message.warning('Сохранённые данные исследования недоступны');
      }
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'Не удалось открыть запись');
    }
  };

  // ── Рендер ──
  const stats = statsQuery.data;
  const branches = result?.ranked_branches ?? [];

  const exploreTab = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card>
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Input.TextArea
            rows={3}
            placeholder="Опишите идею: «Что если Аркаим не был разрушен?», «Путешествие героя через Гиперборею…»"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            style={{ fontSize: 15 }}
          />
          <Row gutter={16} align="middle" wrap>
            <Col>
              <Space>
                <Text type="secondary">Эпоха:</Text>
                <Select
                  placeholder="Эпоха"
                  value={epoch}
                  onChange={setEpoch}
                  options={epochOptions}
                  style={{ width: 200 }}
                  loading={epochsQuery.isLoading}
                />
              </Space>
            </Col>
            <Col>
              <Space>
                <Text type="secondary">Ветвей:</Text>
                <InputNumber min={2} max={8} value={branchCount} onChange={(v) => setBranchCount(v ?? 3)} />
              </Space>
            </Col>
            <Col flex="auto" style={{ textAlign: 'right' }}>
              <Space>
                <Button onClick={() => validateMutation.mutate()} loading={validateMutation.isPending} disabled={prompt.trim().length < 5}>
                  Проверить идею
                </Button>
                <Button type="primary" onClick={() => exploreMutation.mutate()} disabled={!canExplore} loading={exploreMutation.isPending}>
                  Исследовать
                </Button>
              </Space>
            </Col>
          </Row>
        </Space>
      </Card>

      {compatibility && (
        <Card size="small" title="Совместимость с каноном">
          <Row gutter={16} align="middle">
            <Col>
              <Progress
                type="circle"
                percent={pct(compatibility.overall_score)}
                size={64}
                strokeColor={RISK_COLORS[compatibility.risk_level] ?? '#1890ff'}
              />
            </Col>
            <Col>
              <Space direction="vertical">
                <Text strong>{compatibility.overall_score.toFixed(2)} балл</Text>
                <Tag color={RISK_COLORS[compatibility.risk_level] ?? 'default'}>{compatibility.risk_level.toUpperCase()}</Tag>
                {compatibility.is_compatible && <Tag color="green">ОК</Tag>}
              </Space>
            </Col>
            <Col flex="auto">
              <Space wrap size={8}>
                {compatibility.axis_scores.map((ax) => (
                  <div key={ax.axis} style={{ textAlign: 'center', width: 84 }}>
                    <Progress
                      type="circle"
                      percent={pct(ax.score)}
                      size={44}
                      strokeColor={ax.score >= 0.7 ? '#52c41a' : ax.score >= 0.4 ? '#faad14' : '#ff4d4f'}
                    />
                    <div style={{ fontSize: 10, marginTop: 2 }}>{CRITERIA_LABELS[ax.axis] ?? ax.axis}</div>
                  </div>
                ))}
              </Space>
            </Col>
          </Row>
          {compatibility.recommendations.length > 0 && (
            <Alert style={{ marginTop: 12 }} type="info" showIcon message={compatibility.recommendations[0]} />
          )}
        </Card>
      )}

      {exploreMutation.isPending && (
        <Card size="small">
          <Space>
            <Progress percent={66} status="active" />
            <Text type="secondary">Идёт исследование мира… (проверка совместимости → гипотезы → сценарии → ранжирование)</Text>
          </Space>
        </Card>
      )}

      {result && !exploreMutation.isPending && (
        <Card title="Результаты исследования" size="small">
          <Paragraph type="secondary">{result.summary}</Paragraph>
          <Row gutter={[16, 8]} style={{ marginBottom: 12 }}>
            <Col><Text>Гипотеза: <b>{result.hypothesis?.title ?? '—'}</b></Text></Col>
            <Col><Text>Ветвей: <b>{result.scenario.branch_count}</b></Text></Col>
            <Col><Text>Время: <b>{result.duration_ms.toFixed(0)} мс</b></Text></Col>
          </Row>
          {branches.length === 0 ? (
            <Empty description="Гипотезы не сгенерированы — попробуйте перефразировать идею" />
          ) : (
            <Row gutter={[12, 12]}>
              {branches.map((b) => (
                <Col key={b.rank} xs={24} sm={12} md={8}>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => {
                      setSelectedBranch(b);
                      setGeneratedText(null);
                    }}
                    style={{ border: b.rank === 1 ? '2px solid #52c41a' : '1px solid #f0f0f0' }}
                  >
                    <Space direction="vertical" size={8} style={{ width: '100%' }}>
                      <Space>
                        <Tag color={b.rank === 1 ? 'green' : 'blue'}>#{b.rank}</Tag>
                        <BranchTypeTag type={b.branch_type} />
                      </Space>
                      <Text strong style={{ fontSize: 13 }}>{b.title}</Text>
                      <Progress percent={pct(b.quality_score)} size="small" strokeColor={scoreColor(b.quality_score)} />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Влияние: {pct(b.impact_score)}% · Противоречия: {b.contradictions} · Изменения: {b.delta_changes}
                      </Text>
                      <Button size="small" type="link" style={{ paddingLeft: 0 }}>
                        Подробнее →
                      </Button>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Card>
      )}

      {!result && !exploreMutation.isPending && branches.length === 0 && (
        <Empty description="Введите идею и нажмите «Исследовать»" style={{ marginTop: 24 }} />
      )}
    </Space>
  );

  const hypothesesTab = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card size="small">
        <Space>
          <Text type="secondary">Эпоха:</Text>
          <Select value={epoch} onChange={setEpoch} options={epochOptions} style={{ width: 250 }} loading={epochsQuery.isLoading} />
        </Space>
      </Card>
      {hypQuery.isLoading ? (
        <Card size="small" loading />
      ) : (hypQuery.data ?? []).length === 0 ? (
        <Empty description="Нет гипотез для выбранной эпохи" />
      ) : (
        (hypQuery.data ?? []).map((h: Hypothesis) => (
          <Card key={h.id} size="small">
            <Row justify="space-between" align="middle">
              <Col flex="auto">
                <Space direction="vertical" size={2}>
                  <Space>
                    <Tag>{h.type}</Tag>
                    <Text strong>{h.title}</Text>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>{h.description}</Text>
                </Space>
              </Col>
              <Col>
                <Button
                  type="primary"
                  size="small"
                  loading={hypExplore.isPending}
                  disabled={hypExplore.isPending}
                  onClick={() => hypExplore.mutate({ id: h.id, ep: h.epoch ?? epoch ?? 'satya_yuga' })}
                >
                  Исследовать
                </Button>
              </Col>
            </Row>
          </Card>
        ))
      )}
    </Space>
  );

  const possibilitiesTab = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card size="small">
        <Space>
          <Text type="secondary">Эпоха:</Text>
          <Select value={epoch} onChange={setEpoch} options={epochOptions} style={{ width: 250 }} loading={epochsQuery.isLoading} />
        </Space>
      </Card>
      {possQuery.isLoading ? (
        <Card size="small" loading />
      ) : (possQuery.data ?? []).length === 0 ? (
        <Empty description="Нет возможностей для выбранной эпохи" />
      ) : (
        (possQuery.data ?? []).map((p: Possibility, i) => (
          <Card key={p.id ?? i} size="small">
            <Space direction="vertical" size={2}>
              {p.category && <Tag color="blue">{p.category}</Tag>}
              <Text strong>{p.title_ru ?? p.title ?? '—'}</Text>
              {p.description && <Text type="secondary" style={{ fontSize: 12 }}>{p.description}</Text>}
            </Space>
          </Card>
        ))
      )}
    </Space>
  );

  const historyTab = (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {historyQuery.isLoading ? (
        <Card size="small" loading />
      ) : (historyQuery.data ?? []).length === 0 ? (
        <Empty description="История пуста — исследуйте мир, и результаты появятся здесь" />
      ) : (
        (historyQuery.data ?? []).map((item: HistoryItem) => (
          <Card key={item.id} size="small">
            <Row justify="space-between" align="middle">
              <Col flex="auto">
                <Space direction="vertical" size={2}>
                  <Text strong>{item.prompt}</Text>
                  <Space size={8} wrap>
                    {item.epoch && <Tag>{item.epoch}</Tag>}
                    {item.branch_count_actual != null && <Tag color="blue">{item.branch_count_actual} ветвей</Tag>}
                    {item.created_at && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {new Date(item.created_at).toLocaleString('ru-RU')}
                      </Text>
                    )}
                  </Space>
                </Space>
              </Col>
              <Col>
                <Space>
                  <Button size="small" onClick={() => void openFromHistory(item.id)}>Открыть</Button>
                  <Button size="small" danger onClick={() => deleteHist.mutate(item.id)} loading={deleteHist.isPending}>
                    Удалить
                  </Button>
                </Space>
              </Col>
            </Row>
          </Card>
        ))
      )}
    </Space>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1000 }}>
      <div>
        <Title level={3} style={{ margin: 0 }}>
          Исследование мира
        </Title>
        <Paragraph type="secondary">
          Задайте «что если…» про мир книги — и система проложит альтернативные линии его развития,
          проверит их на совместимость с каноном и ранжирует по качеству.
        </Paragraph>
      </div>

      {stats && (
        <Row gutter={[16, 16]}>
          <Col xs={12} sm={6}><Card><Statistic title="Эпох" value={stats.epochs_count} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Локаций" value={stats.locations_count} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Паттернов" value={stats.patterns_count} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="Событий" value={stats.events_count} /></Card></Col>
        </Row>
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          { key: 'explore', label: 'Исследовать', children: exploreTab },
          { key: 'hypotheses', label: 'Гипотезы', children: hypothesesTab },
          { key: 'possibilities', label: 'Возможности', children: possibilitiesTab },
          { key: 'history', label: 'История', children: historyTab },
        ]}
      />

      <Modal
        title={selectedBranch?.title ?? 'Детали ветви'}
        open={!!selectedBranch}
        onCancel={closeModal}
        width={720}
        footer={[
          <Button key="gen" type="primary" loading={genMutation.isPending} onClick={() => genMutation.mutate()}>
            Сгенерировать текст
          </Button>,
          <Button key="close" onClick={closeModal}>Закрыть</Button>,
        ]}
      >
        {selectedBranch && (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Space>
              <BranchTypeTag type={selectedBranch.branch_type} />
              <Text>#{selectedBranch.rank}</Text>
            </Space>
            <Divider style={{ margin: 0 }} />
            <Title level={5} style={{ margin: 0 }}>Критерии качества</Title>
            <Progress percent={pct(selectedBranch.quality_score)} strokeColor={scoreColor(selectedBranch.quality_score)} />
            <Row gutter={16}>
              <Col flex="auto">
                <Text strong>Сильные стороны:</Text>
                {selectedBranch.strengths.length > 0 ? (
                  <div>{selectedBranch.strengths.map((s, i) => <Tag key={i} color="green">{s}</Tag>)}</div>
                ) : (
                  <Text type="secondary"> нет</Text>
                )}
              </Col>
              <Col flex="auto">
                <Text strong>Слабые стороны:</Text>
                {selectedBranch.weaknesses.length > 0 ? (
                  <div>{selectedBranch.weaknesses.map((w, i) => <Tag key={i} color="red">{w}</Tag>)}</div>
                ) : (
                  <Text type="secondary"> нет</Text>
                )}
              </Col>
            </Row>
            <Divider style={{ margin: 0 }} />
            <Row gutter={16}>
              <Col><Progress type="circle" percent={pct(selectedBranch.impact_score)} size={56} /><div style={{ fontSize: 11, textAlign: 'center' }}>Влияние</div></Col>
              <Col><Statistic title="Противоречия" value={selectedBranch.contradictions} /></Col>
              <Col><Statistic title="Изменения мира" value={selectedBranch.delta_changes} /></Col>
            </Row>

            {generatedText && (
              <>
                <Divider style={{ margin: 0 }} />
                <Title level={5} style={{ margin: 0 }}>Промпт для генерации текста</Title>
                <Card size="small">
                  <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>System instruction:</Paragraph>
                  <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{generatedText.system_instruction}</Paragraph>
                  <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>User prompt:</Paragraph>
                  <Paragraph style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>{generatedText.user_prompt}</Paragraph>
                </Card>
              </>
            )}

            <Divider style={{ margin: 0 }} />
            <Title level={5} style={{ margin: 0 }}>Оценить ветвь</Title>
            <Space>
              <Rate value={feedbackRating} onChange={setFeedbackRating} />
              <Text type="secondary">ваша оценка (обязательно)</Text>
            </Space>
            <Input.TextArea rows={2} placeholder="Комментарий (необязательно)" value={feedbackComment} onChange={(e) => setFeedbackComment(e.target.value)} />
            <Button
              type="primary"
              size="small"
              disabled={feedbackRating === 0}
              loading={feedbackMutation.isPending}
              onClick={() => feedbackMutation.mutate()}
            >
              Отправить оценку
            </Button>
          </Space>
        )}
      </Modal>
    </div>
  );
}

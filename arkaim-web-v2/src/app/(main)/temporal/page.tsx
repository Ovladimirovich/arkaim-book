/**
 * /temporal — «Время мира» (F3_SPEC §1; reader+).
 *
 * Контракты (live-факт F3-шаг 0):
 *   GET /book/temporal/chain → цепочка эпох (12 узлов, 11 PRECEDES-связей)
 *   GET /book/temporal/nodes → 13 узлов: 12 эпох + temporal_today (наблюдатель)
 *   GET /book/temporal/context/{epoch_id} → детали эпохи
 *   POST /book/temporal/future-extrapolation → сценарии будущего (reader)
 *
 * ADR_TEMPORAL §5 — КРИТИЧЕСКИЕ ИНВАРИАНТЫ ЭКРАНА:
 *   1. Цепочка рендерится ТОЛЬКО из backend-данных (nodes/relations).
 *      Фронт НЕ синтезирует связи. Отсутствующий relation (Современность →
 *      Аркаим) остаётся отсутствующим: temporal_today НЕ в цепочке.
 *   2. Сегодня = точка наблюдения (HYPOTHESIS-бейдж), НЕ эпоха цепочки.
 *   3. Каждый сценарий будущего — с обязательным бейджем FUTURE_EXTRAPOLATION.
 */
'use client';

import { Alert, App, Button, Card, Col, Input, Row, Space, Statistic, Tag, Timeline, Typography } from 'antd';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import {
  ApiError,
  extrapolateFuture,
  getTemporalChain,
  getTemporalContext,
  getTemporalNodes,
  type TemporalNode,
} from '@/shared/api';
import { ProvenanceBadge, ProvenanceBadgeList } from '@/shared/ui/ProvenanceBadge';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;

export default function TemporalPage() {
  const { message } = App.useApp();
  const [direction, setDirection] = useState<'FORWARD' | 'BACKWARD'>('BACKWARD');
  const [selectedEra, setSelectedEra] = useState<string | null>(null);
  const [futurePrompt, setFuturePrompt] = useState('');

  // ── Цепочка эпох (инвариант: рендер только backend nodes/relations) ──
  const chain = useQuery({
    queryKey: ['temporal', 'chain', direction],
    queryFn: () => getTemporalChain(direction),
    staleTime: 5 * 60_000,
  });

  // ── Все узлы (включая temporal_today — точку наблюдателя) ──
  const nodes = useQuery({
    queryKey: ['temporal', 'nodes'],
    queryFn: () => getTemporalNodes(),
    staleTime: 5 * 60_000,
  });

  // ── Контекст выбранной эпохи ──
  const context = useQuery({
    queryKey: ['temporal', 'context', selectedEra],
    queryFn: () => getTemporalContext(selectedEra!),
    enabled: selectedEra !== null,
    staleTime: 60_000,
  });

  // ── Сценарии будущего (M8; работает без LLM — детерминированный паттерн) ──
  const future = useMutation({
    mutationFn: () =>
      extrapolateFuture({
        prompt: futurePrompt.trim() || 'каким будет мир Аркаима дальше?',
        max_futures: 3,
      }),
    onError: (e) => {
      message.error(e instanceof ApiError ? e.message : 'Не удалось построить сценарии');
    },
  });

  const chainData = chain.data;
  const todayNode: TemporalNode | undefined = (nodes.data ?? []).find((n) => n.id === 'temporal_today');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 900 }}>
      <Title level={3} style={{ margin: 0 }}>
        Время мира
      </Title>
      <Paragraph type="secondary">
        Временная цепочка эпох мира книги. Каждая эпоха — с указанием происхождения: канон автора,
        внешние источники, реконструкция. Связи между эпохами заданы моделью мира, а не собраны
        на этой странице.
      </Paragraph>

      {/* ── Цепочка эпох ── */}
      <StateView
        data={chainData}
        loading={chain.isLoading}
        error={(chain.error as ApiError | null) ?? null}
        onRetry={() => void chain.refetch()}
      >
        {(d) => (
          <Card
            title="Цепочка эпох"
            extra={
              <Space>
                <Tag>{d.direction}</Tag>
                <Text type="secondary">
                  {d.stats.nodes} эпох · {d.stats.relations} связей
                </Text>
              </Space>
            }
          >
            <Space direction="vertical" size={2} style={{ marginBottom: 16 }}>
              <Button size="small" onClick={() => setDirection(direction === 'BACKWARD' ? 'FORWARD' : 'BACKWARD')}>
                Направление: {direction === 'BACKWARD' ? 'от древних к новым' : 'от новых к древним'}
              </Button>
            </Space>
            <Timeline
              items={d.nodes.map((n) => ({
                color: n.is_anchor ? 'gold' : 'blue',
                dot: n.is_anchor ? <Tag color="gold">Якорь</Tag> : undefined,
                children: (
                  <div
                    style={{ cursor: 'pointer', paddingBottom: 4 }}
                    onClick={() => setSelectedEra(n.era_id || n.id)}
                  >
                    <Space direction="vertical" size={2}>
                      <Space wrap>
                        <Text strong>{n.label}</Text>
                        {n.is_anchor && <Tag color="gold">Якорь Аркаима</Tag>}
                        <Text type="secondary">{n.confidence != null ? `${Math.round(n.confidence * 100)}%` : ''}</Text>
                      </Space>
                      <ProvenanceBadgeList tags={n.provenance} />
                      {n.notes ? <Text type="secondary" style={{ fontSize: 12 }}>{n.notes}</Text> : null}
                    </Space>
                  </div>
                ),
              }))}
            />
          </Card>
        )}
      </StateView>

      {/* ── Современность: точка наблюдателя (ВНЕ цепочки — инвариант ADR §5) ── */}
      {todayNode && (
        <Card size="small" title="Современность — точка наблюдателя">
          <Space direction="vertical" size={4}>
            <Space wrap>
              <Text strong>{todayNode.label}</Text>
              <Text type="secondary">
                {todayNode.bounds?.start ?? ''}
              </Text>
            </Space>
            <ProvenanceBadgeList tags={todayNode.provenance} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              Методологическая точка отсчёта для реконструкции — не эпоха исторической цепочки и не
              источник связей.
            </Text>
          </Space>
        </Card>
      )}

      {/* ── Детали эпохи ── */}
      {selectedEra && (
        <StateView
          data={context.data}
          loading={context.isLoading}
          error={(context.error as ApiError | null) ?? null}
          onRetry={() => void context.refetch()}
        >
          {(ctx) => (
            <Card
              title={`Эпоха: ${ctx.epoch?.name_ru || ctx.epoch?.name || selectedEra}`}
              extra={<Button size="small" onClick={() => setSelectedEra(null)}>Закрыть</Button>}
            >
              {ctx.epoch?.description && (
                <Paragraph>{ctx.epoch.description}</Paragraph>
              )}
              <ProvenanceBadgeList tags={ctx.epoch?.provenance ?? []} />
              <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                <Col span={8}>
                  <Statistic title="События" value={ctx.event_count} />
                </Col>
                <Col span={8}>
                  <Statistic title="Персонажи" value={ctx.character_count} />
                </Col>
                <Col span={8}>
                  <Statistic title="Технологии" value={ctx.technology_count} />
                </Col>
              </Row>
              {ctx.characters?.length > 0 && (
                <Paragraph type="secondary" style={{ marginTop: 12 }}>
                  Персонажи эпохи:{' '}
                  {ctx.characters.map((c) => c.name || c.id).join(', ')}
                </Paragraph>
              )}
              {ctx.events?.length > 0 && (
                <Paragraph type="secondary">
                  События: {ctx.events.map((e) => e.name || e.id).join(', ')}
                </Paragraph>
              )}
            </Card>
          )}
        </StateView>
      )}

      {/* ── Будущее мира (M8-экстраполяция; обязательный бейдж FUTURE_EXTRAPOLATION) ── */}
      <Card title="Будущее мира" extra={<Text type="secondary">проекция от канона</Text>}>
        <Paragraph type="secondary">
          Сценарии будущего строятся проекцией от канона книги. Это не предсказание: каждый
          сценарий — экстраполяция и помечен соответствующим происхождением.
        </Paragraph>
        <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
          <Input
            value={futurePrompt}
            onChange={(e) => setFuturePrompt(e.target.value)}
            placeholder="Например: что будет с наследием Аркаима?"
            onPressEnter={() => future.mutate()}
            disabled={future.isPending}
          />
          <Button type="primary" loading={future.isPending} onClick={() => future.mutate()}>
            Построить
          </Button>
        </Space.Compact>

        {future.data && (
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {future.data.scenarios.map((s, i) => (
              <Card
                key={i}
                size="small"
                title={
                  <Space wrap>
                    <ProvenanceBadge category="FUTURE_EXTRAPOLATION" confidence={0.5} />
                    <Text type="secondary">Сценарий {i + 1}</Text>
                    <Tag color={s.is_compatible ? 'green' : 'red'}>
                      {s.is_compatible ? 'совместим' : 'конфликтен'} · {Math.round(s.compatibility_score * 100)}%
                    </Tag>
                    <Tag>риск: {s.risk_level}</Tag>
                  </Space>
                }
              >
                <Paragraph style={{ marginBottom: 0 }}>{s.description}</Paragraph>
              </Card>
            ))}
            <Text type="secondary" style={{ fontSize: 12 }}>
              {future.data.provenance_note}
            </Text>
          </Space>
        )}
      </Card>

      <Alert
        type="info"
        showIcon
        message="Время мира строится моделью мира книги"
        description="Эта страница отображает только связи и происхождение, которые заданы бэкендом. Между «Современностью» и эпохами нет временных связей, пока модель мира их не содержит."
      />
    </div>
  );
}

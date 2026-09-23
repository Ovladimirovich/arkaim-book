/**
 * /studio — Studio v2: рабочее место автора.
 *
 * Пользовательский сценарий:
 *   открыть → создать/выбрать session → видеть три описания →
 *   обсудить → исправить → получить новую version →
 *   variant → reference → finalize → export
 *
 * Studio НЕ генерирует описания — получает от Description System.
 */
'use client';

import { App, Button, Card, Col, Collapse, Divider, Empty, Input, List, Modal, Popconfirm, Row, Select, Skeleton, Space, Statistic, Steps, Tag, Timeline, Tooltip, Typography, Upload, message, theme } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useRef } from 'react';
import {
  ApiError,
  createStudioSession,
  listStudioSessions,
  listStudioScenes,
  getStudioSession,
  studioDiscuss,
  studioModify,
  studioCreateVariants,
  studioActivateVersion,
  studioApprove,
  studioReject,
  studioExport,
  studioUploadReference,
  deleteStudioSession,
  type StudioSession,
  type StudioVersion,
  type StudioMessage,
  type ReferenceAsset,
  type StudioExport as StudioExportType,
  type MediaPlanSummary,
  type VideoScenarioSummary,
} from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { useToken } = theme;

const STATUS_COLORS: Record<string, string> = {
  draft: 'default',
  discussing: 'processing',
  approved: 'success',
  rejected: 'error',
  sent: 'warning',
};

const DERIVATION_COLORS: Record<string, string> = {
  initial: 'blue',
  adaptation: 'orange',
  variation: 'purple',
};

// ── Main Page ──────────────────────────────────────────────────

export default function StudioPage() {
  const { message: msgApi } = App.useApp();
  const qc = useQueryClient();
  const { token } = useToken();
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'image' | 'video' | 'scenario'>('image');

  // ── Sessions list ────────────────────────────────────────────

  const sessionsQ = useQuery({
    queryKey: ['studio', 'sessions'],
    queryFn: () => listStudioSessions({ limit: 50 }),
    retry: false,
  });

  // ── Selected session detail ──────────────────────────────────

  const sessionQ = useQuery({
    queryKey: ['studio', 'session', selectedSessionId],
    queryFn: () => getStudioSession(selectedSessionId!),
    enabled: !!selectedSessionId,
    retry: false,
  });

  const session = sessionQ.data?.session;
  const versions = sessionQ.data?.versions ?? [];
  const messages = sessionQ.data?.messages ?? [];
  const references = sessionQ.data?.references ?? [];
  const activeVersion = versions.find((v) => v.is_active) ?? versions[versions.length - 1];

  // ── Create session ───────────────────────────────────────────

  const [createOpen, setCreateOpen] = useState(false);
  const [createChapter, setCreateChapter] = useState(1);
  const [createSceneId, setCreateSceneId] = useState('');

  const scenesQ = useQuery({
    queryKey: ['studio', 'scenes'],
    queryFn: () => listStudioScenes(),
    retry: false,
  });

  const createMut = useMutation({
    mutationFn: () => createStudioSession(createChapter, createSceneId),
    onSuccess: (data) => {
      msgApi.success(`Сессия создана: ${data.session.title}`);
      qc.invalidateQueries({ queryKey: ['studio', 'sessions'] });
      setSelectedSessionId(data.session.session_id);
      setCreateOpen(false);
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка создания'),
  });

  // ── Discuss ──────────────────────────────────────────────────

  const [discussMsg, setDiscussMsg] = useState('');
  const discussRef = useRef<HTMLDivElement>(null);

  const discussMut = useMutation({
    mutationFn: () => studioDiscuss(selectedSessionId!, discussMsg),
    onSuccess: () => {
      setDiscussMsg('');
      qc.invalidateQueries({ queryKey: ['studio', 'session', selectedSessionId] });
      setTimeout(() => discussRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка обсуждения'),
  });

  // ── Modify ───────────────────────────────────────────────────

  const [modifyOpen, setModifyOpen] = useState(false);
  const [modifyTarget, setModifyTarget] = useState('image_description');
  const [modifyField, setModifyField] = useState('atmosphere');
  const [modifyValue, setModifyValue] = useState('');
  const [modifyNote, setModifyNote] = useState('');

  const modifyMut = useMutation({
    mutationFn: () => studioModify(selectedSessionId!, {
      target: modifyTarget,
      field_path: modifyField,
      new_value: modifyValue,
      note: modifyNote,
    }),
    onSuccess: () => {
      msgApi.success('Новая версия создана');
      qc.invalidateQueries({ queryKey: ['studio', 'session', selectedSessionId] });
      setModifyOpen(false);
      setModifyValue('');
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка изменения'),
  });

  // ── Variants ─────────────────────────────────────────────────

  const variantMut = useMutation({
    mutationFn: () => studioCreateVariants(selectedSessionId!, 2),
    onSuccess: (data) => {
      msgApi.success(`Создано ${data.length} вариантов`);
      qc.invalidateQueries({ queryKey: ['studio', 'session', selectedSessionId] });
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка вариантов'),
  });

  // ── Activate version ─────────────────────────────────────────

  const activateMut = useMutation({
    mutationFn: (versionId: string) => studioActivateVersion(selectedSessionId!, versionId),
    onSuccess: () => {
      msgApi.success('Версия активирована');
      qc.invalidateQueries({ queryKey: ['studio', 'session', selectedSessionId] });
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка активации'),
  });

  // ── Approve / Reject ────────────────────────────────────────

  const approveMut = useMutation({
    mutationFn: () => studioApprove(selectedSessionId!),
    onSuccess: () => {
      msgApi.success('Сессия утверждена');
      qc.invalidateQueries({ queryKey: ['studio', 'session', selectedSessionId] });
      qc.invalidateQueries({ queryKey: ['studio', 'sessions'] });
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка утверждения'),
  });

  const rejectMut = useMutation({
    mutationFn: () => studioReject(selectedSessionId!, 'Rejected by author'),
    onSuccess: () => {
      msgApi.info('Сессия отклонена');
      qc.invalidateQueries({ queryKey: ['studio', 'session', selectedSessionId] });
      qc.invalidateQueries({ queryKey: ['studio', 'sessions'] });
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка отклонения'),
  });

  // ── Delete session ──────────────────────────────────────────

  const deleteMut = useMutation({
    mutationFn: () => deleteStudioSession(selectedSessionId!),
    onSuccess: () => {
      msgApi.success('Сессия удалена');
      setSelectedSessionId(null);
      qc.invalidateQueries({ queryKey: ['studio', 'sessions'] });
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка удаления'),
  });

  // ── Export ───────────────────────────────────────────────────

  const [exportData, setExportData] = useState<StudioExportType | null>(null);
  const [exportOpen, setExportOpen] = useState(false);

  const exportMut = useMutation({
    mutationFn: () => studioExport(selectedSessionId!),
    onSuccess: (data) => {
      setExportData(data);
      setExportOpen(true);
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка экспорта'),
  });

  // ── Reference upload ────────────────────────────────────────

  const [refDesc, setRefDesc] = useState('');

  const uploadMut = useMutation({
    mutationFn: (file: File) => studioUploadReference(selectedSessionId!, file, refDesc),
    onSuccess: () => {
      msgApi.success('Reference загружен');
      qc.invalidateQueries({ queryKey: ['studio', 'session', selectedSessionId] });
      setRefDesc('');
    },
    onError: (e) => msgApi.error(e instanceof ApiError ? e.message : 'Ошибка загрузки'),
  });

  // ── Render ───────────────────────────────────────────────────

  if (sessionsQ.isLoading) return <Skeleton active paragraph={{ rows: 8 }} />;
  if (sessionsQ.isError) return <StateView data={undefined} loading={false} error={{ message: 'Не удалось загрузить сессии' }}>{() => null}</StateView>;

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>Studio</Title>
        <Space>
          <Button type="primary" onClick={() => setCreateOpen(true)}>
            Новая сессия
          </Button>
        </Space>
      </Row>

      <Row gutter={24}>
        {/* ── Left: Session list ── */}
        <Col xs={24} md={6}>
          <Card title="Сессии" size="small" styles={{ body: { padding: 0 } }}>
            {sessionsQ.data && sessionsQ.data.length === 0 && (
              <Empty description="Нет сессий" style={{ padding: 24 }} />
            )}
            <List
              dataSource={sessionsQ.data ?? []}
              renderItem={(s) => (
                <List.Item
                  onClick={() => setSelectedSessionId(s.session_id)}
                  style={{
                    cursor: 'pointer',
                    background: s.session_id === selectedSessionId ? token.colorPrimaryBg : undefined,
                    padding: '8px 16px',
                  }}
                >
                  <List.Item.Meta
                    title={<Text ellipsis>{s.title || s.scene_id}</Text>}
                    description={
                      <Space size={4}>
                        <Tag color={STATUS_COLORS[s.status]}>{s.status}</Tag>
                        <Text type="secondary" style={{ fontSize: 11 }}>{s.updated_at?.slice(0, 10)}</Text>
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* ── Right: Session detail ── */}
        <Col xs={24} md={18}>
          {!selectedSessionId && (
            <Card>
              <div style={{ textAlign: 'center', padding: '24px 20px' }}>
                <Title level={4} style={{ color: token.colorTextSecondary }}>Studio — рабочее место автора</Title>
                <Paragraph style={{ color: token.colorTextSecondary, maxWidth: 600, margin: '12px auto 24px' }}>
                  Studio получает три описания сцены из Arkaim Description System
                  и позволяет вам обсуждать, корректировать и финализировать их перед отправкой в производство.
                  Studio <strong>не генерирует</strong> содержание — только уточняет.
                </Paragraph>
                <Button type="primary" size="large" onClick={() => setCreateOpen(true)} style={{ marginBottom: 24 }}>
                  Создать сессию
                </Button>

                <Collapse
                  style={{ textAlign: 'left', maxWidth: 700, margin: '0 auto' }}
                  defaultActiveKey={['overview']}
                  items={[
                    {
                      key: 'overview',
                      label: <Text strong>Что такое Studio?</Text>,
                      children: (
                        <div>
                          <Paragraph>
                            <strong>Studio</strong> — это инструмент для автора. Здесь вы работаете с описаниями сцен,
                            которые Arkaim подготовил автоматически. Ваша задача — проверить, обсудить и довести их до готовности.
                          </Paragraph>
                          <Paragraph>
                            Каждая сцена получает <strong>три описания</strong>:
                          </Paragraph>
                          <ul style={{ paddingLeft: 20 }}>
                            <li><strong>Image Description</strong> — описание для генерации одного кадра (промпт, атмосфера, стиль)</li>
                            <li><strong>Video Description</strong> — описание для видеоролика (длительность, FPS, движение камеры)</li>
                            <li><strong>Full Video Scenario</strong> — полный сценарий (планы, камера, действия персонажей, монтажные переходы, ритм, звук)</li>
                          </ul>
                        </div>
                      ),
                    },
                    {
                      key: 'step1',
                      label: <Text strong>Шаг 1. Создание сессии</Text>,
                      children: (
                        <div>
                          <ol style={{ paddingLeft: 20 }}>
                            <li>Нажмите <strong>«Создать сессию»</strong> вверху</li>
                            <li>Выберите сцену из списка (сцены берутся из генома книги)</li>
                            <li>Arkaim автоматически получит три описания из Description System</li>
                          </ol>
                          <Paragraph type="secondary" style={{ fontSize: 12 }}>
                            Это может занять несколько секунд — Arkaim строит визуальный контекст сцены.
                          </Paragraph>
                        </div>
                      ),
                    },
                    {
                      key: 'step2',
                      label: <Text strong>Шаг 2. Просмотр описаний</Text>,
                      children: (
                        <div>
                          <Paragraph>
                            После создания сессии вы видите три вкладки: <strong>Image Description</strong>, <strong>Video Description</strong>, <strong>Full Video Scenario</strong>.
                            Переключайтесь между ними, чтобы увидеть каждое описание.
                          </Paragraph>
                          <Paragraph>
                            Если описание вас устраивает — переходите сразу к шагу 5 (Утверждение).
                          </Paragraph>
                        </div>
                      ),
                    },
                    {
                      key: 'step3',
                      label: <Text strong>Шаг 3. Обсуждение</Text>,
                      children: (
                        <div>
                          <Paragraph>
                            Если хотите что-то обсудить — используйте панель <strong>«Обсуждение»</strong> внизу.
                            Напишите, что вас смущает или что хотите изменить. Arkaim ответит текстом.
                          </Paragraph>
                          <Paragraph>
                            <strong>Важно:</strong> обсуждение — это только диалог. Оно <strong>не изменяет</strong> описания.
                            Чтобы применить изменения, используйте «Изменить» (шаг 4).
                          </Paragraph>
                        </div>
                      ),
                    },
                    {
                      key: 'step4',
                      label: <Text strong>Шаг 4. Внесение изменений</Text>,
                      children: (
                        <div>
                          <Paragraph>
                            Когда решили, что менять — нажмите <strong>«Изменить»</strong> в заголовке сессии:
                          </Paragraph>
                          <ol style={{ paddingLeft: 20 }}>
                            <li><strong>Описание</strong> — выберите какое из трёх описаний менять</li>
                            <li><strong>Поле</strong> — какое поле (атмосфера, промпт, стиль и т.д.)</li>
                            <li><strong>Новое значение</strong> — введите новый текст</li>
                            <li><strong>Примечание</strong> — объясните почему меняете (необязательно)</li>
                          </ol>
                          <Paragraph>
                            После нажатия «Применить» создаётся <strong>новая версия</strong>. Старая версия сохраняется.
                            Вы можете вернуться к любой версии через таймлайн версий.
                          </Paragraph>
                          <Paragraph>
                            <strong>Варианты:</strong> кнопка «Варианты» автоматически создаст 2 альтернативных версии
                            текущего описания (копирует содержание, не генерирует новое).
                          </Paragraph>
                        </div>
                      ),
                    },
                    {
                      key: 'step5',
                      label: <Text strong>Шаг 5. Утверждение и экспорт</Text>,
                      children: (
                        <div>
                          <Paragraph>
                            Когда описание готово — нажмите <strong>«Утвердить»</strong>. Сессия получит статус <Tag color="success">approved</Tag>.
                          </Paragraph>
                          <Paragraph>
                            После утверждения появится кнопка <strong>«Экспорт»</strong>. Нажмите её, чтобы получить
                            финальный StudioExport — готовый к отправке в производство (arkaim-media).
                          </Paragraph>
                          <Paragraph>
                            Экспорт содержит: все три описания, историю версий, reference-изображения.
                            Не содержит execution-параметров (model, steps, seed) — это решает media-pipeline, а не автор.
                          </Paragraph>
                        </div>
                      ),
                    },
                    {
                      key: 'tips',
                      label: <Text strong>Полезные советы</Text>,
                      children: (
                        <ul style={{ paddingLeft: 20 }}>
                          <li><strong>Reference-изображения</strong> — загружайте картинки, которые помогут Arkaim понять вашу задумку</li>
                          <li><strong>Версии</strong> — не бойтесь экспериментировать. Все версии сохраняются, можно вернуться к любой</li>
                          <li><strong>Удаление</strong> — кнопка «Удалить» в заголовке удалит всю сессию безвозвратно</li>
                          <li><strong>Discussion ≠ версия</strong> — обсуждение не создаёт новую версию, только «Изменить» создаёт</li>
                        </ul>
                      ),
                    },
                  ]}
                />
              </div>
            </Card>
          )}

          {selectedSessionId && sessionQ.isLoading && <Skeleton active paragraph={{ rows: 12 }} />}

          {selectedSessionId && sessionQ.isError && (
            <StateView data={undefined} loading={false} error={{ message: 'Не удалось загрузить сессию' }}>{() => null}</StateView>
          )}

          {session && activeVersion && (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {/* Session header */}
              <Card size="small">
                <Row justify="space-between" align="middle">
                  <Space>
                    <Title level={4} style={{ margin: 0 }}>{session.title}</Title>
                    <Tag color={STATUS_COLORS[session.status]}>{session.status}</Tag>
                    <Text type="secondary">v{activeVersion.version_number}</Text>
                  </Space>
                  <Space>
                    {session.status !== 'approved' && session.status !== 'rejected' && (
                      <>
                        <Button size="small" onClick={() => variantMut.mutate()} loading={variantMut.isPending}>
                          Варианты
                        </Button>
                        <Button size="small" onClick={() => setModifyOpen(true)}>
                          Изменить
                        </Button>
                        <Button size="small" type="primary" onClick={() => approveMut.mutate()} loading={approveMut.isPending}>
                          Утвердить
                        </Button>
                      </>
                    )}
                    {session.status === 'approved' && (
                      <Button size="small" type="primary" onClick={() => exportMut.mutate()} loading={exportMut.isPending}>
                        Экспорт
                      </Button>
                    )}
                    <Popconfirm
                      title="Удалить сессию?"
                      description="Все версии и обсуждения будут удалены"
                      onConfirm={() => deleteMut.mutate()}
                      okText="Удалить"
                      cancelText="Отмена"
                    >
                      <Button size="small" danger loading={deleteMut.isPending}>
                        Удалить
                      </Button>
                    </Popconfirm>
                  </Space>
                </Row>
              </Card>

              {/* Three descriptions */}
              <Card size="small" title="Описания сцены">
                <div style={{ marginBottom: 12 }}>
                  <Space>
                    <Button size="small" type={activeTab === 'image' ? 'primary' : 'default'} onClick={() => setActiveTab('image')}>
                      Image Description
                    </Button>
                    <Button size="small" type={activeTab === 'video' ? 'primary' : 'default'} onClick={() => setActiveTab('video')}>
                      Video Description
                    </Button>
                    <Button size="small" type={activeTab === 'scenario' ? 'primary' : 'default'} onClick={() => setActiveTab('scenario')}>
                      Full Video Scenario
                    </Button>
                  </Space>
                </div>
                {activeTab === 'image' && <MediaPlanView plan={activeVersion.image_description} label="Image" token={token} />}
                {activeTab === 'video' && <MediaPlanView plan={activeVersion.video_description} label="Video" token={token} />}
                {activeTab === 'scenario' && <VideoScenarioView scenario={activeVersion.video_scenario} token={token} />}
              </Card>

              {/* Version timeline */}
              <Card size="small" title={`Версии (${versions.length})`}>
                <Timeline
                  items={versions.map((v) => ({
                    color: v.is_active ? 'green' : v.is_final ? 'blue' : 'gray',
                    children: (
                      <Space direction="vertical" size={0}>
                        <Space>
                          <Text strong>v{v.version_number}</Text>
                          <Tag color={DERIVATION_COLORS[v.derivation] ?? 'default'}>{v.derivation}</Tag>
                          {v.is_active && <Tag color="green">active</Tag>}
                          {v.is_final && <Tag color="blue">final</Tag>}
                          {!v.is_active && !v.is_final && session.status !== 'approved' && (
                            <Button size="small" type="link" onClick={() => activateMut.mutate(v.version_id)}>
                              Активировать
                            </Button>
                          )}
                        </Space>
                        {v.note && <Text type="secondary" style={{ fontSize: 12 }}>{v.note}</Text>}
                        {v.user_modifications.length > 0 && (
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {v.user_modifications.map((m) => `${m.target}.${m.field_path}`).join(', ')}
                          </Text>
                        )}
                      </Space>
                    ),
                  }))}
                />
              </Card>

              {/* Discussion */}
              <Card size="small" title="Обсуждение" ref={discussRef}>
                <div style={{ maxHeight: 300, overflow: 'auto', marginBottom: 12 }}>
                  {messages.filter((m) => m.role !== 'system').length === 0 && (
                    <Text type="secondary">Нет сообщений. Начните обсуждение ниже.</Text>
                  )}
                  {messages.filter((m) => m.role !== 'system').map((m) => (
                    <div key={m.message_id} style={{
                      marginBottom: 8,
                      padding: '8px 12px',
                      borderRadius: 8,
                      background: m.role === 'user' ? token.colorPrimaryBg : token.colorSuccessBg,
                      marginLeft: m.role === 'user' ? 40 : 0,
                      marginRight: m.role === 'assistant' ? 40 : 0,
                    }}>
                      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
                        {m.role === 'user' ? 'Вы' : 'Arkaim'} · {m.created_at?.slice(11, 16)}
                      </Text>
                      <Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{m.content}</Paragraph>
                    </div>
                  ))}
                </div>
                {session.status !== 'approved' && session.status !== 'rejected' && (
                  <div style={{ marginTop: 12 }}>
                    <TextArea
                      value={discussMsg}
                      onChange={(e) => setDiscussMsg(e.target.value)}
                      placeholder="Опишите, что хотите изменить..."
                      autoSize={{ minRows: 2, maxRows: 6 }}
                      style={{ marginBottom: 8 }}
                      onPressEnter={(e) => {
                        if (!e.shiftKey && discussMsg.trim()) {
                          e.preventDefault();
                          discussMut.mutate();
                        }
                      }}
                    />
                    <Button
                      type="primary"
                      onClick={() => discussMut.mutate()}
                      loading={discussMut.isPending}
                      disabled={!discussMsg.trim()}
                      block
                    >
                      Отправить
                    </Button>
                  </div>
                )}
              </Card>

              {/* References */}
              <Card size="small" title={`Reference Images (${references.length})`}>
                {references.length === 0 && <Text type="secondary">Нет reference-изображений</Text>}
                <Row gutter={[12, 12]}>
                  {references.map((r) => (
                    <Col key={r.asset_id}>
                      <Card size="small" style={{ width: 160 }}>
                        <Text ellipsis style={{ fontSize: 12 }}>{r.description || r.asset_id}</Text>
                      </Card>
                    </Col>
                  ))}
                </Row>
                {session.status !== 'approved' && session.status !== 'rejected' && (
                  <div style={{ marginTop: 12 }}>
                    <Space>
                      <Input
                        placeholder="Описание reference..."
                        value={refDesc}
                        onChange={(e) => setRefDesc(e.target.value)}
                        style={{ width: 240 }}
                      />
                      <Upload
                        showUploadList={false}
                        beforeUpload={(file) => {
                          uploadMut.mutate(file);
                          return false;
                        }}
                      >
                        <Button loading={uploadMut.isPending}>Загрузить</Button>
                      </Upload>
                    </Space>
                  </div>
                )}
              </Card>
            </Space>
          )}
        </Col>
      </Row>

      {/* ── Create session modal ── */}
      <Modal
        title="Новая Studio-сессия"
        open={createOpen}
        onOk={() => {
          if (!createSceneId) { msgApi.warning('Выберите сцену'); return; }
          createMut.mutate();
        }}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={createMut.isPending}
        okText="Создать"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text strong>Выберите сцену:</Text>
            <Select
              value={createSceneId || undefined}
              onChange={(val) => {
                setCreateSceneId(val);
                const scene = scenesQ.data?.find(s => s.scene_id === val);
                if (scene) setCreateChapter(scene.chapter);
              }}
              placeholder="Сцена из генома книги..."
              style={{ width: '100%', marginTop: 8 }}
              showSearch
              optionFilterProp="label"
              loading={scenesQ.isLoading}
              options={(scenesQ.data ?? []).map(s => ({
                value: s.scene_id,
                label: `Глава ${s.chapter}: ${s.title}`,
              }))}
            />
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Три описания (Image Description, Video Description, Full Video Scenario)
            будут автоматически получены из Arkaim Description System.
            Studio не генерирует — только корректирует.
          </Text>
        </Space>
      </Modal>

      {/* ── Modify modal ── */}
      <Modal
        title="Изменить описание"
        open={modifyOpen}
        onOk={() => modifyMut.mutate()}
        onCancel={() => setModifyOpen(false)}
        confirmLoading={modifyMut.isPending}
        okText="Применить"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text>Описание:</Text>
            <Select
              value={modifyTarget}
              onChange={setModifyTarget}
              style={{ width: '100%' }}
              options={[
                { value: 'image_description', label: 'Image Description' },
                { value: 'video_description', label: 'Video Description' },
                { value: 'video_scenario', label: 'Full Video Scenario' },
              ]}
            />
          </div>
          <div>
            <Text>Поле:</Text>
            <Select
              value={modifyField}
              onChange={setModifyField}
              style={{ width: '100%' }}
              options={[
                { value: 'atmosphere', label: 'Atmosphere' },
                { value: 'prompt', label: 'Prompt' },
                { value: 'visual_style', label: 'Visual Style' },
                { value: 'synopsis', label: 'Synopsis (scenario)' },
                { value: 'direction_notes', label: 'Direction Notes (scenario)' },
              ]}
            />
          </div>
          <div>
            <Text>Новое значение:</Text>
            <TextArea
              value={modifyValue}
              onChange={(e) => setModifyValue(e.target.value)}
              autoSize={{ minRows: 2, maxRows: 6 }}
              placeholder="Введите новое значение..."
            />
          </div>
          <div>
            <Text>Примечание:</Text>
            <Input value={modifyNote} onChange={(e) => setModifyNote(e.target.value)} placeholder="Почему изменяете..." />
          </div>
        </Space>
      </Modal>

      {/* ── Export modal ── */}
      <Modal
        title="StudioExport"
        open={exportOpen}
        onOk={() => {
          navigator.clipboard.writeText(JSON.stringify(exportData, null, 2));
          msgApi.success('Скопировано в буфер');
        }}
        onCancel={() => setExportOpen(false)}
        okText="Копировать JSON"
        width={700}
      >
        {exportData && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={8}><Statistic title="Image" value={exportData.image_description ? '✓' : '—'} /></Col>
              <Col span={8}><Statistic title="Video" value={exportData.video_description ? '✓' : '—'} /></Col>
              <Col span={8}><Statistic title="Scenario" value={exportData.video_scenario ? '✓' : '—'} /></Col>
            </Row>
            <Statistic title="References" value={exportData.references.length} />
            <Statistic title="Version lineage" value={exportData.version_lineage.length} suffix="versions" />
            <Text type="secondary">Lineage: {exportData.version_lineage.join(' → ')}</Text>
          </Space>
        )}
      </Modal>
    </div>
  );
}

// ── Sub-views ──────────────────────────────────────────────────

function MediaPlanView({ plan, label, token }: { plan: MediaPlanSummary | null; label: string; token: any }) {
  if (!plan) return <Empty description={`${label} не доступно`} />;
  return (
    <div style={{ padding: 12, background: token.colorFillQuaternary, borderRadius: 8, border: `1px solid ${token.colorBorderSecondary}` }}>
      <Row gutter={[16, 8]}>
        <Col span={24}><Text strong>Промпт:</Text> <Text>{plan.prompt || '—'}</Text></Col>
        {plan.atmosphere && <Col span={12}><Text strong>Атмосфера:</Text> <Text>{plan.atmosphere}</Text></Col>}
        {plan.visual_style && <Col span={12}><Text strong>Стиль:</Text> <Text>{plan.visual_style}</Text></Col>}
        {plan.media_kind === 'video' && plan.duration_sec && (
          <Col span={12}><Text strong>Длительность:</Text> <Text>{plan.duration_sec} сек</Text></Col>
        )}
        {plan.media_kind === 'video' && plan.fps && (
          <Col span={12}><Text strong>FPS:</Text> <Text>{plan.fps}</Text></Col>
        )}
      </Row>
    </div>
  );
}

function VideoScenarioView({ scenario, token }: { scenario: VideoScenarioSummary | null; token: any }) {
  if (!scenario) return <Empty description="Scenario не доступно" />;
  return (
    <div style={{ padding: 12, background: token.colorFillQuaternary, borderRadius: 8, border: `1px solid ${token.colorBorderSecondary}` }}>
      <Row gutter={[16, 8]}>
        <Col span={24}><Text strong>Название:</Text> <Text>{scenario.title}</Text></Col>
        <Col span={24}><Text strong>Синопсис:</Text> <Text>{scenario.synopsis}</Text></Col>
        <Col span={12}><Text strong>Длительность:</Text> <Text>{scenario.total_duration_sec} сек</Text></Col>
        <Col span={12}><Text strong>Планов:</Text> <Text>{scenario.shots.length}</Text></Col>
      </Row>
      {scenario.shots.length > 0 && (
        <>
          <Divider style={{ margin: '12px 0 8px' }} />
          <Text strong>Планы:</Text>
          <Timeline
            style={{ marginTop: 8 }}
            items={scenario.shots.map((s) => ({
              children: (
                <Space>
                  <Tag>{s.shot_type}</Tag>
                  <Text>{s.description}</Text>
                  {s.duration_sec && <Text type="secondary">({s.duration_sec}s)</Text>}
                </Space>
              ),
            }))}
          />
        </>
      )}
      {scenario.direction_notes && (
        <>
          <Divider style={{ margin: '12px 0 8px' }} />
          <Text strong>Режиссёрские заметки:</Text>
          <Paragraph style={{ margin: '4px 0 0', whiteSpace: 'pre-wrap' }}>{scenario.direction_notes}</Paragraph>
        </>
      )}
    </div>
  );
}

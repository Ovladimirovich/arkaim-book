/**
 * /upload — загрузка документов в BOOK OS pipeline.
 *
 * Контракты (backend):
 *   POST /book/os/pipeline/ingest?doc_type=&version= → IngestResult  (editor+)
 *   GET  /book/os/documents                         → Document[]      (reader+)
 *
 * RBAC: page gated by RoleGate (editor/admin). Reader gets no-access text.
 * Auth: credentials: 'same-origin' (cookie-сессия).
 */
'use client';

import { useState } from 'react';
import { App, Button, Card, Popconfirm, Select, Space, Table, Tag, Typography, Upload } from 'antd';
import { InboxOutlined, CheckCircleOutlined, FileTextOutlined, DeleteOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RoleGate } from '@/shared/rbac/RoleGate';
import { listDocuments, uploadDocument, deleteDocument, type Document, type IngestResult } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;

// ── Константы ────────────────────────────────────────────────────────────

const ACCEPTED_TYPES = '.txt,.md,.json,.pdf,.doc,.docx';
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

const DOC_TYPES: { value: string; label: string }[] = [
  { value: 'primary_source', label: 'Основной источник' },
  { value: 'secondary_source', label: 'Вторичный источник' },
  { value: 'external',       label: 'Внешний документ' },
];

// ── No-access fallback ───────────────────────────────────────────────────

const noAccess = (
  <Paragraph type="secondary">
    Загрузка документов доступна редактору и администратору.
    Связаться с администратором для получения доступа.
  </Paragraph>
);

// ── Страница ─────────────────────────────────────────────────────────────

export default function UploadPage() {
  const { message: msgApi } = App.useApp();
  const qc = useQueryClient();
  const [docType, setDocType] = useState('primary_source');
  const [version, setVersion] = useState('1.0.0');

  // ── Список документов ──────────────────────────────────────────────────

  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ['os', 'documents'],
    queryFn: () => listDocuments(),
    staleTime: 60_000,
  });

  // ── Загрузка ───────────────────────────────────────────────────────────

  const uploadMut = useMutation({
    mutationFn: (file: File) => uploadDocument(file, docType, version),
    onSuccess: (result: IngestResult) => {
      if (result.status === 'ok') {
        msgApi.success(
          `«${result.title}» обработан: ${result.chunks_count} чанков, ` +
          `${result.entities_added ?? 0} сущностей, ${result.facts_added ?? 0} фактов`,
        );
        void qc.invalidateQueries({ queryKey: ['os', 'documents'] });
      } else {
        msgApi.error(result.errors?.[0] ?? 'Документ не обработан');
      }
    },
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : 'Ошибка загрузки';
      msgApi.error(msg);
    },
  });

  // ── beforeUpload: валидация размера, возврат false чтобы Ant не делал свой XHR ─
  const handleBeforeUpload = (file: File) => {
    if (file.size > MAX_FILE_SIZE) {
      msgApi.error(`Файл слишком большой (макс. 50 MB): ${file.name}`);
      return false;
    }
    uploadMut.mutate(file);
    return false;
  };

  // ── Колонки таблицы ────────────────────────────────────────────────────

  const columns = [
    {
      title: 'Название',
      dataIndex: 'title',
      key: 'title',
      render: (t: string) => <Space><FileTextOutlined />{t}</Space>,
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      render: (t: string) => {
        const colors: Record<string, string> = {
          primary_source: 'blue',
          secondary_source: 'green',
          external: 'default',
        };
        return <Tag color={colors[t] ?? 'default'}>{t.replace('_', ' ')}</Tag>;
      },
    },
    { title: 'Версия', dataIndex: 'version', key: 'version', width: 90 },
    {
      title: 'Чанки',
      dataIndex: 'chunks_count',
      key: 'chunks_count',
      width: 80,
      render: (n: number) => n ? <Tag color="geekblue">{n}</Tag> : '—',
    },
    {
      title: 'Загружено',
      dataIndex: 'imported_at',
      key: 'imported_at',
      render: (v: string) => new Date(v).toLocaleString('ru-RU'),
      sorter: (a: Document, b: Document) =>
        new Date(a.imported_at).getTime() - new Date(b.imported_at).getTime(),
    },
    {
      title: '',
      key: 'action',
      width: 60,
      render: (_: unknown, record: Document) => (
        <Popconfirm
          title="Удалить документ"
          description={`«${record.title}»?`}
          okText="Удалить"
          cancelText="Отмена"
          okButtonProps={{ danger: true }}
          onConfirm={async () => {
            try {
              await deleteDocument(record.id);
              msgApi.success('Документ удалён');
              void qc.invalidateQueries({ queryKey: ['os', 'documents'] });
            } catch (e) {
              const msg = e instanceof Error ? e.message : 'Ошибка удаления';
              msgApi.error(msg);
            }
          }}
        >
          <Button type="text" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <RoleGate roles={['editor', 'admin']} fallback={noAccess}>
      <div style={{ maxWidth: 860, margin: '0 auto', padding: '24px 0' }}>
        <Title level={3} style={{ marginBottom: 8 }}>Загрузка документов</Title>
        <Paragraph type="secondary" style={{ marginBottom: 24 }}>
          Загрузите источник для обработки BOOK OS pipeline. Документ будет про chunking,
          извлечение сущностей/фактов/связей и индексация в ChromaDB.
        </Paragraph>

        {/* ── Форма загрузки ── */}
        <Card title="Новый документ" style={{ marginBottom: 24 }}>
          <Upload.Dragger
            accept={ACCEPTED_TYPES}
            multiple={false}
            beforeUpload={handleBeforeUpload}
            showUploadList={false}
            disabled={uploadMut.isPending}
            style={{ marginBottom: 16 }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ color: '#1677ff' }} />
            </p>
            <p className="ant-upload-text">Перетащите файл сюда или нажмите для выбора</p>
            <p className="ant-upload-hint">
              PDF · TXT · MD · JSON · DOC · DOCX &nbsp;·&nbsp; макс. 50 MB
            </p>
          </Upload.Dragger>

          {/* Конфигурация */}
          <Space wrap>
            <Select
              value={docType}
              onChange={setDocType}
              options={DOC_TYPES}
              style={{ width: 200 }}
              disabled={uploadMut.isPending}
            />
            <input
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              disabled={uploadMut.isPending}
              style={{ width: 110, padding: '4px 8px', borderRadius: 6, border: '1px solid #d9d9d9' }}
              placeholder="1.0.0"
            />
            <Text type="secondary" style={{ fontSize: 12 }}>версия документа</Text>
          </Space>

          {uploadMut.isPending && (
            <Paragraph type="secondary" style={{ marginTop: 12 }}>
              <CheckCircleOutlined style={{ color: '#1677ff' }} /> Обработка…
            </Paragraph>
          )}
        </Card>

        {/* ── Список документов ── */}
        <Card title="Загруженные документы">
          <StateView<Document[]>
            data={docs}
            loading={docsLoading}
            error={null}
            empty={!docsLoading && (!docs || docs.length === 0)}
            onRetry={() => void qc.invalidateQueries({ queryKey: ['os', 'documents'] })}
          >
            {(data) => (
              <Table<Document>
                dataSource={data}
                columns={columns}
                rowKey="id"
                pagination={{ pageSize: 10, showSizeChanger: false }}
                size="small"
              />
            )}
          </StateView>
        </Card>
      </div>
    </RoleGate>
  );
}

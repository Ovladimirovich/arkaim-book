'use client';

import { useState, useCallback } from 'react';
import { UploadOutlined, InboxOutlined, CheckCircleOutlined, FileTextOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LButton } from '@/shared/ui/light/LButton';
import { LSelect } from '@/shared/ui/light/LSelect';
import { LInput } from '@/shared/ui/light/LInput';
import { LUpload } from '@/shared/ui/light/LUpload';
import { LTable } from '@/shared/ui/light/LTable';
import { LTag } from '@/shared/ui/light/LTag';
import { LProgress } from '@/shared/ui/light/LProgress';
import { LStatistic } from '@/shared/ui/light/LStatistic';
import { LAlert } from '@/shared/ui/light/LAlert';
import { LDivider } from '@/shared/ui/light/LDivider';
import { LSpace } from '@/shared/ui/light/LSpace';

type UploadHistory = {
  id: string;
  filename: string;
  doc_type: string;
  version: string;
  status: string;
  created_at: string;
  chunks?: number;
};

const DOC_TYPES = [
  { value: 'primary_source', label: 'Основной источник' },
  { value: 'secondary_source', label: 'Вторичный источник' },
  { value: 'external', label: 'Внешний документ' },
];

const ACCEPTED_TYPES = '.txt,.md,.json,.pdf,.doc,.docx';
const MAX_FILE_SIZE = 50 * 1024 * 1024;

function UploadForm({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('primary_source');
  const [version, setVersion] = useState('1.0.0');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [msg, setMsg] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null);

  const beforeUpload = useCallback((f: File) => {
    const isValidSize = f.size <= MAX_FILE_SIZE;
    if (!isValidSize) {
      setMsg({ type: 'error', text: `Файл слишком большой. Максимум: 50MB` });
      return false;
    }
    setFile(f);
    setResult(null);
    setMsg(null);
    return false;
  }, []);

  const handleUpload = async () => {
    if (!file) { setMsg({ type: 'warning', text: 'Выберите файл' }); return; }
    setUploading(true);
    setProgress(0);
    setMsg(null);

    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + 10, 90));
    }, 200);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const cookie = document.cookie.split('; ').find(c => c.startsWith('arkaim_session='))?.split('=')[1] || '';
      const resp = await fetch(`/book/os/pipeline/ingest?doc_type=${docType}&version=${version}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${cookie}` },
        body: formData,
      });
      const data = await resp.json();
      setResult(data);
      setProgress(100);
      setMsg({ type: 'success', text: 'Документ обработан' });
      onUploadComplete();
    } catch {
      setMsg({ type: 'error', text: 'Ошибка загрузки' });
      setProgress(0);
    } finally {
      clearInterval(progressInterval);
      setUploading(false);
    }
  };

  return (
    <LCard title="Новый документ" style={{ marginBottom: 16 }}>
      <LUpload
        accept={ACCEPTED_TYPES}
        maxCount={1}
        beforeUpload={beforeUpload}
        showUploadList={!!file}
        disabled={uploading}
      >
        <InboxOutlined style={{ fontSize: 40, color: '#999' }} />
        <p style={{ margin: '8px 0 0', color: '#333', fontWeight: 500 }}>Нажмите или перетащите файл</p>
        <p style={{ margin: '4px 0 0', fontSize: 12, color: '#999' }}>
          Поддерживаются: .txt, .md, .json, .pdf, .doc, .docx (макс. 50MB)
        </p>
      </LUpload>

      <div style={{ display: 'flex', gap: 16, marginTop: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 180 }}>
          <span style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Тип документа</span>
          <LSelect value={docType} onChange={setDocType} options={DOC_TYPES} style={{ width: '100%' }} />
        </div>
        <div style={{ flex: 1, minWidth: 180 }}>
          <span style={{ display: 'block', marginBottom: 4, fontSize: 13, fontWeight: 500 }}>Версия</span>
          <LInput value={version} onChange={e => setVersion(e.target.value)} placeholder="1.0.0" />
        </div>
        <div style={{ flex: 1, minWidth: 180, display: 'flex', alignItems: 'flex-end' }}>
          <LButton type="primary" block onClick={handleUpload} loading={uploading} disabled={!file} icon={<UploadOutlined />} style={{ height: 36 }}>
            Загрузить и обработать
          </LButton>
        </div>
      </div>

      {uploading && (
        <LProgress percent={progress} status="active" style={{ marginTop: 16 }} />
      )}

      {result && (
        <LAlert
          type={result.status === 'ok' || !result.error ? 'success' : 'error'}
          icon={<CheckCircleOutlined />}
          title="Документ обработан"
          description={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <span>Статус: <LTag color="green">{result.status || 'ok'}</LTag></span>
              {result.chunks && <span>Извлечено чанков: {result.chunks}</span>}
              {result.entities && <span>Найдено сущностей: {result.entities}</span>}
            </div>
          }
          style={{ marginTop: 16 }}
        />
      )}

      {msg && !result && (
        <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 6, background: msg.type === 'success' ? '#f0fdf4' : msg.type === 'error' ? '#fef2f2' : '#fffbeb', border: `1px solid ${msg.type === 'success' ? '#bbf7d0' : msg.type === 'error' ? '#fecaca' : '#fed7aa'}`, color: msg.type === 'success' ? '#166534' : msg.type === 'error' ? '#991b1b' : '#92400e', fontSize: 13 }}>
          {msg.text}
        </div>
      )}
    </LCard>
  );
}

function UploadHistoryPanel() {
  const [history, setHistory] = useState<UploadHistory[]>(() => {
    if (typeof window !== 'undefined') {
      try { return JSON.parse(localStorage.getItem('upload_history') || '[]'); } catch { return []; }
    }
    return [];
  });

  const addToHistory = (result: Record<string, unknown>, filename: string, docType: string, version: string) => {
    setHistory(prev => {
      const next = [{ id: Date.now().toString(), filename, doc_type: docType, version, status: (result?.status as string) || 'ok', created_at: new Date().toISOString(), chunks: result?.chunks as number | undefined }, ...prev].slice(0, 20);
      localStorage.setItem('upload_history', JSON.stringify(next));
      return next;
    });
  };

  const columns = [
    { title: 'Файл', dataIndex: 'filename', key: 'filename', render: (v: unknown) => <LSpace><FileTextOutlined />{v as string}</LSpace> },
    { title: 'Тип', dataIndex: 'doc_type', key: 'type', render: (v: unknown) => <LTag>{v as string}</LTag> },
    { title: 'Версия', dataIndex: 'version', key: 'version', render: (v: unknown) => v as string },
    { title: 'Статус', dataIndex: 'status', key: 'status', render: (v: unknown) => <LTag color="green">{v as string}</LTag> },
    { title: 'Чанки', dataIndex: 'chunks', key: 'chunks', render: (v: unknown) => v != null ? String(v) : '—' },
    { title: 'Время', dataIndex: 'created_at', key: 'time', render: (v: unknown) => new Date(v as string).toLocaleString('ru') },
  ];

  return (
    <LCard title="История загрузок" extra={<LTag>{history.length} файлов</LTag>}>
      {history.length === 0 ? (
        <span style={{ color: '#999' }}>Пока нет загруженных файлов</span>
      ) : (
        <LTable columns={columns} dataSource={history} rowKey="id" size="small" pagination={{ pageSize: 5 }} />
      )}
    </LCard>
  );
}

function FormatsInfo() {
  const formats = [
    { ext: '.txt', name: 'Текст', desc: 'Обычный текстовый файл' },
    { ext: '.md', name: 'Markdown', desc: 'Форматированный текст' },
    { ext: '.json', name: 'JSON', desc: 'Структурированные данные' },
    { ext: '.pdf', name: 'PDF', desc: 'Документ (извлечение текста)' },
    { ext: '.doc', name: 'Word', desc: 'Документ Microsoft Word' },
    { ext: '.docx', name: 'Word (新版)', desc: 'Документ Microsoft Word' },
  ];

  const columns = [
    { title: 'Расширение', dataIndex: 'ext', key: 'ext', render: (v: unknown) => <code>{v as string}</code> },
    { title: 'Формат', dataIndex: 'name', key: 'name', render: (v: unknown) => v as string },
    { title: 'Описание', dataIndex: 'desc', key: 'desc', render: (v: unknown) => v as string },
  ];

  return (
    <LCard title="Поддерживаемые форматы" size="small">
      <LTable dataSource={formats} rowKey="ext" size="small" pagination={false} columns={columns} />
    </LCard>
  );
}

function UploadContent() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2><UploadOutlined /> Загрузка документов</h2>
      <p style={{ color: '#666' }}>
        Загружайте документы для обновления базы знаний книги «Наследие Аркаима».
        Система автоматически извлечёт текст, сущности и связи.
      </p>

      <LAlert
        title="Важно"
        description="Загружайте только те документы, которые относятся к книге. Система автоматически обработает и индексирует содержимое."
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 60%', minWidth: 300 }}>
          <UploadForm onUploadComplete={() => setRefreshKey(k => k + 1)} />
        </div>
        <div style={{ flex: '1 1 35%', minWidth: 250 }}>
          <FormatsInfo />
        </div>
      </div>

      <LDivider />

      <UploadHistoryPanel key={refreshKey} />
    </div>
  );
}

export default function UploadPage() {
  return (
    <ProtectedRoute>
      <UploadContent />
    </ProtectedRoute>
  );
}
'use client';

import { useState, useCallback } from 'react';
import { LCard, LButton, LTag, LSpace, LInput, LAlert, LTable, LSelect, LTextArea, LTabs, LBadge, LModal, toast } from '@/shared/ui/light';
import { KeyOutlined, CodeOutlined, DeleteOutlined, CaretRightOutlined, HistoryOutlined, BookOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';

type ApiKey = {
  id: string;
  key_prefix: string;
  name?: string;
  last_used_at?: string;
  is_active: boolean;
  created_at: string;
};

type TestResult = {
  endpoint: string;
  method: string;
  status: number;
  data: Record<string, unknown>;
  time: number;
  timestamp: Date;
};

function ApiKeysPanel() {
  const queryClient = useQueryClient();
  const [newKey, setNewKey] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<ApiKey | null>(null);

  const { data: keys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.get<ApiKey[]>('/auth/api-keys'),
  });

  const createMutation = useMutation({
    mutationFn: (name: string) => api.post<{ key: string; key_masked: string }>('/auth/api-key', null, { method: 'POST' }),
    onSuccess: (data) => {
      setNewKey(data.key);
      toast.success('API-ключ создан');
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/api-keys/${id}`),
    onSuccess: () => {
      toast.success('API-ключ удалён');
      setDeleteConfirm(null);
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
    },
  });

  const columns = [
    { title: 'Префикс', dataIndex: 'key_prefix', key: 'prefix', render: (v: unknown) => <code>{String(v)}...</code> },
    { title: 'Имя', dataIndex: 'name', key: 'name', render: (v: unknown) => String(v || '—') },
    { title: 'Последнее использование', dataIndex: 'last_used_at', key: 'last_used', render: (v: unknown) => v ? new Date(String(v)).toLocaleString('ru') : 'Никогда' },
    { title: 'Статус', dataIndex: 'is_active', key: 'status', render: (v: unknown) => v ? <LTag color="green">Активен</LTag> : <LTag color="red">Удалён</LTag> },
    {
      title: '', key: 'actions',
      render: (_: unknown, record: unknown) => {
        const r = record as ApiKey;
        return r.is_active ? (
          <LButton size="small" danger icon={<DeleteOutlined />} onClick={() => setDeleteConfirm(r)} />
        ) : null;
      },
    },
  ];

  return (
    <div>
      <LSpace style={{ marginBottom: 16 }}>
        <LButton type="primary" icon={<KeyOutlined />} onClick={() => createMutation.mutate('web-app')}>
          Создать ключ
        </LButton>
      </LSpace>

      <LModal open={!!deleteConfirm} title="Удалить ключ?" onCancel={() => setDeleteConfirm(null)}
        footer={<><LButton onClick={() => setDeleteConfirm(null)}>Отмена</LButton><LButton type="primary" danger onClick={() => deleteConfirm && deleteMutation.mutate(deleteConfirm.id)}>Удалить</LButton></>}>
        <span>Вы уверены, что хотите удалить ключ {deleteConfirm?.key_prefix}?</span>
      </LModal>

      {newKey && (
        <LAlert
          type="success"
          message="Новый API-ключ"
          description={
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <code>{newKey}</code>
              <span style={{ color: '#faad14', fontSize: 12 }}>
                Сохраните ключ — он показывается только один раз!
              </span>
            </div>
          }
          closable
          onClose={() => setNewKey(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <LTable columns={columns} dataSource={keys || []} rowKey="id" loading={isLoading} size="small" />
    </div>
  );
}

function ApiTesterPanel() {
  const [method, setMethod] = useState('GET');
  const [endpoint, setEndpoint] = useState('/book/health');
  const [body, setBody] = useState('');
  const [result, setResult] = useState<TestResult | null>(null);
  const [history, setHistory] = useState<TestResult[]>([]);
  const [loading, setLoading] = useState(false);

  const endpoints = [
    { value: '/book/health', label: 'GET /book/health — Статус сервиса' },
    { value: '/book/genome', label: 'GET /book/genome — Геном книги' },
    { value: '/book/layers', label: 'GET /book/layers — Слои сознания' },
    { value: '/book/ask', label: 'POST /book/ask — Задать вопрос' },
    { value: '/book/reader/profile', label: 'GET /book/reader/profile — Профиль' },
    { value: '/book/reader/history', label: 'GET /book/reader/history — История' },
    { value: '/book/reader/history/stats', label: 'GET /book/reader/history/stats — Статистика' },
    { value: '/auth/me', label: 'GET /auth/me — Пользователь' },
    { value: '/auth/api-keys', label: 'GET /auth/api-keys — Ключи' },
    { value: '/xray/stats', label: 'GET /xray/stats — X-Ray' },
    { value: '/analytics', label: 'GET /analytics — Аналитика' },
  ];

  const runTest = useCallback(async () => {
    setLoading(true);
    const start = Date.now();
    try {
      let data: Record<string, unknown>;
      if (method === 'GET') {
        data = await api.get(endpoint);
      } else if (method === 'POST') {
        data = await api.post(endpoint, body ? JSON.parse(body) : undefined);
      } else if (method === 'DELETE') {
        data = await api.delete(endpoint);
      } else {
        data = await api.get(endpoint);
      }
      const testResult: TestResult = { endpoint, method, status: 200, data, time: Date.now() - start, timestamp: new Date() };
      setResult(testResult);
      setHistory(prev => [testResult, ...prev].slice(0, 20));
    } catch (err: unknown) {
      const error = err as { status?: number; data?: Record<string, unknown>; message?: string };
      const testResult: TestResult = { endpoint, method, status: error.status || 500, data: error.data || { error: error.message }, time: Date.now() - start, timestamp: new Date() };
      setResult(testResult);
      setHistory(prev => [testResult, ...prev].slice(0, 20));
    } finally {
      setLoading(false);
    }
  }, [method, endpoint, body]);

  return (
    <div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <LSpace wrap>
          <LSelect value={method} onChange={setMethod} options={[{ value: 'GET', label: 'GET' }, { value: 'POST', label: 'POST' }, { value: 'DELETE', label: 'DELETE' }]} style={{ width: 100 }} />
          <LSelect value={endpoint} onChange={setEndpoint} options={endpoints} style={{ width: 400 }} placeholder="Выберите эндпоинт" />
          <LButton type="primary" icon={<CaretRightOutlined />} onClick={runTest} loading={loading}>
            Выполнить
          </LButton>
        </LSpace>

        {method !== 'GET' && (
          <LTextArea value={body} onChange={e => setBody(e.target.value)} placeholder='{"question": "Кто такой Велик?"}' rows={3} />
        )}

        {result && (
          <LCard size="small" title="Результат">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <LSpace>
                <LTag color={result.status < 400 ? 'green' : 'red'}>{result.status}</LTag>
                <span style={{ color: '#999', fontSize: 12 }}>{result.time}ms</span>
                <span style={{ color: '#999', fontSize: 11 }}>{result.timestamp.toLocaleTimeString('ru')}</span>
              </LSpace>
              <pre style={{ background: 'var(--surface-bg)', padding: 12, borderRadius: 6, fontSize: 12, overflow: 'auto', maxHeight: 300, margin: 0 }}>
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </div>
          </LCard>
        )}

        {history.length > 0 && (
          <LCard size="small" title={<><HistoryOutlined /> История запросов</>}>
            {history.map((item, i) => (
              <div key={i} style={{ cursor: 'pointer', padding: '6px 8px', borderRadius: 4 }}
                onClick={() => { setMethod(item.method); setEndpoint(item.endpoint); }}>
                <LSpace>
                  <LTag color={item.status < 400 ? 'green' : 'red'} style={{ minWidth: 45 }}>{item.status}</LTag>
                  <code style={{ fontSize: 12 }}>{item.method}</code>
                  <span style={{ fontSize: 13 }}>{item.endpoint}</span>
                  <span style={{ color: '#999', fontSize: 11 }}>{item.time}ms</span>
                </LSpace>
              </div>
            ))}
          </LCard>
        )}
      </div>
    </div>
  );
}

function ApiExamplesPanel() {
  const examples = [
    {
      title: 'Задать вопрос книге',
      method: 'POST',
      endpoint: '/book/ask',
      curl: `curl -X POST http://localhost:8642/book/ask \\
  -H "Content-Type: application/json" \\
  -d '{"question": "Кто такой Велик?"}'`,
      python: `import requests

resp = requests.post("http://localhost:8642/book/ask",
    json={"question": "Кто такой Велик?"})
print(resp.json())`,
    },
    {
      title: 'Получить геном книги',
      method: 'GET',
      endpoint: '/book/genome',
      curl: `curl http://localhost:8642/book/genome`,
      python: `import requests

resp = requests.get("http://localhost:8642/book/genome")
print(resp.json())`,
    },
    {
      title: 'Профиль читателя',
      method: 'GET',
      endpoint: '/book/reader/profile',
      curl: `curl http://localhost:8642/book/reader/profile \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
      python: `import requests

resp = requests.get("http://localhost:8642/book/reader/profile",
    headers={"Authorization": "Bearer YOUR_API_KEY"})
print(resp.json())`,
    },
    {
      title: 'История вопросов',
      method: 'GET',
      endpoint: '/book/reader/history?limit=10',
      curl: `curl "http://localhost:8642/book/reader/history?limit=10" \\
  -H "Authorization: Bearer YOUR_API_KEY"`,
      python: `import requests

resp = requests.get("http://localhost:8642/book/reader/history",
    params={"limit": 10},
    headers={"Authorization": "Bearer YOUR_API_KEY"})
print(resp.json())`,
    },
    {
      title: 'Создать API-ключ',
      method: 'POST',
      endpoint: '/auth/api-key',
      curl: `curl -X POST http://localhost:8642/auth/api-key \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"`,
      python: `import requests

resp = requests.post("http://localhost:8642/auth/api-key",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"})
print(resp.json())`,
    },
  ];

  const [selected, setSelected] = useState(0);

  return (
    <div>
      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ width: 250, flexShrink: 0 }}>
          {examples.map((item, index) => (
            <div key={index} style={{ cursor: 'pointer', background: selected === index ? '#f1f5f9' : undefined, borderRadius: 6, padding: '8px 12px' }}
              onClick={() => setSelected(index)}>
              <LSpace>
                <LTag color={item.method === 'GET' ? 'blue' : 'green'}>{item.method}</LTag>
                <span style={{ fontSize: 13 }}>{item.title}</span>
              </LSpace>
            </div>
          ))}
        </div>
        <div style={{ flex: 1 }}>
          {examples[selected] && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <h4 style={{ margin: 0 }}>{examples[selected].title}</h4>
              <code>{examples[selected].method} {examples[selected].endpoint}</code>

              <LCard size="small" title="cURL">
                <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: 12, borderRadius: 6, fontSize: 12, margin: 0, overflow: 'auto' }}>
                  {examples[selected].curl}
                </pre>
              </LCard>

              <LCard size="small" title="Python">
                <pre style={{ background: '#1e293b', color: '#e2e8f0', padding: 12, borderRadius: 6, fontSize: 12, margin: 0, overflow: 'auto' }}>
                  {examples[selected].python}
                </pre>
              </LCard>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ApiDocsPanel() {
  const sections = [
    {
      title: 'Book Intelligence',
      endpoints: [
        { method: 'GET', path: '/book/health', desc: 'Статус сервиса' },
        { method: 'GET', path: '/book/genome', desc: 'Геном книги (темы, персонажи, ценности)' },
        { method: 'GET', path: '/book/layers', desc: 'Слои сознания (knowledge, meaning, identity, mission)' },
        { method: 'POST', path: '/book/ask', desc: 'Задать вопрос книге', body: '{"question": "...", "context": "..."}' },
        { method: 'GET', path: '/book/reader/profile', desc: 'Профиль читателя' },
        { method: 'GET', path: '/book/reader/history', desc: 'История вопросов' },
        { method: 'GET', path: '/book/reader/history/full', desc: 'Полная история (user + assistant)' },
        { method: 'GET', path: '/book/reader/history/sessions', desc: 'Список сессий' },
        { method: 'GET', path: '/book/reader/history/stats', desc: 'Статистика истории' },
      ],
    },
    {
      title: 'Visual Genome',
      endpoints: [
        { method: 'POST', path: '/book/visualize', desc: 'Визуализация сцены', body: '{"chapter": 1, "scene_id": "..."}' },
        { method: 'POST', path: '/book/visual-genome/scene', desc: 'Создать сцену' },
        { method: 'POST', path: '/book/visual-genome/character', desc: 'Создать визуал персонажа' },
        { method: 'POST', path: '/book/visual-genome/location', desc: 'Создать визуал локации' },
        { method: 'POST', path: '/book/visual-genome/from-speech', desc: 'Голосовое описание в визуал', body: '{"text": "..."}' },
      ],
    },
    {
      title: 'Auth',
      endpoints: [
        { method: 'GET', path: '/auth/me', desc: 'Текущий пользователь' },
        { method: 'POST', path: '/auth/api-key', desc: 'Создать API-ключ' },
        { method: 'GET', path: '/auth/api-keys', desc: 'Мои API-ключи' },
        { method: 'GET', path: '/auth/admin/users', desc: 'Все пользователи (admin)' },
        { method: 'POST', path: '/auth/admin/invites', desc: 'Создать инвайт (admin)' },
      ],
    },
    {
      title: 'Observability',
      endpoints: [
        { method: 'GET', path: '/xray/stats', desc: 'Статистика трейсов' },
        { method: 'GET', path: '/xray/traces', desc: 'Список трейсов' },
        { method: 'GET', path: '/analytics', desc: 'Анонимная аналитика' },
        { method: 'GET', path: '/metrics', desc: 'Метрики системы' },
      ],
    },
    {
      title: 'WebSocket',
      endpoints: [
        { method: 'WS', path: '/ws', desc: 'Real-time уведомления (pulse_beat, new_question, chat_response)' },
      ],
    },
  ];

  return (
    <div>
      {sections.map(section => (
        <LCard key={section.title} title={section.title} style={{ marginBottom: 16 }}>
          <LTable
            dataSource={section.endpoints}
            rowKey="path"
            size="small"
            pagination={false}
            columns={[
              {
                title: 'Метод', dataIndex: 'method', key: 'method', width: 80,
                render: (v: unknown) => {
                  const val = String(v);
                  return <LTag color={val === 'GET' ? 'blue' : val === 'POST' ? 'green' : val === 'DELETE' ? 'red' : 'orange'}>{val}</LTag>;
                },
              },
              { title: 'Путь', dataIndex: 'path', key: 'path', render: (v: unknown) => <code>{String(v)}</code> },
              { title: 'Описание', dataIndex: 'desc', key: 'desc' },
              { title: 'Тело', dataIndex: 'body', key: 'body', render: (v: unknown) => v ? <code style={{ fontSize: 11 }}>{String(v)}</code> : '—' },
            ]}
          />
        </LCard>
      ))}
    </div>
  );
}

function ApiContent() {
  const items = [
    { key: 'keys', label: <><KeyOutlined /> API-ключи</>, children: <ApiKeysPanel /> },
    { key: 'tester', label: <><CaretRightOutlined /> Тестер</>, children: <ApiTesterPanel /> },
    { key: 'examples', label: <><BookOutlined /> Примеры</>, children: <ApiExamplesPanel /> },
    { key: 'docs', label: <><CodeOutlined /> Документация</>, children: <ApiDocsPanel /> },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <h2><CodeOutlined /> API</h2>
      <p style={{ color: '#999' }}>
        Управление API-ключами, тестирование эндпоинтов, примеры кода, документация API.
      </p>
      <LTabs items={items} />
    </div>
  );
}

export default function ApiPage() {
  return (
    <ProtectedRoute>
      <ApiContent />
    </ProtectedRoute>
  );
}
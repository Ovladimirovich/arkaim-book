'use client';

import { useState } from 'react';
import { HistoryOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import Link from 'next/link';
import { LCard } from '@/shared/ui/light/LCard';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LAlert } from '@/shared/ui/light/LAlert';
import { LStatistic } from '@/shared/ui/light/LStatistic';

type HistoryItem = {
  id: number;
  session_id: string;
  role?: 'user' | 'assistant';
  content: string;
  created_at: string;
  metadata?: Record<string, unknown>;
};

type HistoryFullItem = HistoryItem & {
  role: 'user' | 'assistant';
};

type SessionSummary = {
  session_id: string;
  created_at: string;
  last_question_at: string;
  question_count: number;
};

type HistoryStats = {
  questions: number;
  sessions: number;
  last_active: string | null;
};

function sessionLabel(s: SessionSummary): string {
  try {
    const d = new Date(s.last_question_at);
    return d.toLocaleDateString('ru', { day: 'numeric', month: 'short' }) +
      ' · ' + s.question_count + ' вопр.';
  } catch {
    return s.session_id.slice(0, 8) + '…';
  }
}

function HistoryContent() {
  const [selectedSession, setSelectedSession] = useState<string>('');
  const [viewMode, setViewMode] = useState<'list' | 'conversation'>('list');
  const queryClient = useQueryClient();

  const { data: stats, isError: statsIsError } = useQuery({
    queryKey: ['history-stats'],
    queryFn: () => api.get<HistoryStats>('/book/reader/history/stats'),
  });

  const { data: sessionsData, isError: sessionsIsError } = useQuery({
    queryKey: ['history-sessions'],
    queryFn: () => api.get<{ data: SessionSummary[] }>('/book/reader/history/sessions'),
  });

  const {
    data: history,
    isLoading: historyLoading,
    isError: historyIsError,
    error: historyError,
  } = useQuery({
    queryKey: ['history', selectedSession],
    queryFn: () => selectedSession
      ? api.get<{ data: HistoryFullItem[] }>(`/book/reader/history/full?session_id=${encodeURIComponent(selectedSession)}&limit=100`)
      : api.get<{ data: HistoryItem[] }>('/book/reader/history?limit=50'),
  });

  const hasError = statsIsError || sessionsIsError || historyIsError;
  const retryHistory = () => {
    void queryClient.invalidateQueries({ queryKey: ['history-stats'] });
    void queryClient.invalidateQueries({ queryKey: ['history-sessions'] });
    void queryClient.invalidateQueries({ queryKey: ['history'] });
  };

  const items = (history?.data ?? []) as (HistoryItem | HistoryFullItem)[];
  const sessions = sessionsData?.data ?? [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, fontWeight: 600, marginBottom: 16 }}>
        <HistoryOutlined /> История вопросов
      </h2>

      {hasError && (
        <LAlert
          type="error"
          showIcon
          message="Не удалось получить реальную историю из памяти читателя"
          description={historyError instanceof Error ? historyError.message : 'Проверьте, что backend запущен и сессия пользователя активна.'}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 16 }}>
        <LCard>
          <LStatistic
            title="Вопросов"
            value={stats?.questions ?? 0}
            valueStyle={{ color: 'var(--foreground)' }}
          />
        </LCard>
        <LCard>
          <LStatistic
            title="Сессий"
            value={stats?.sessions ?? 0}
            valueStyle={{ color: 'var(--foreground)' }}
          />
        </LCard>
        <LCard>
          <LStatistic
            title="Последняя активность"
            value={stats?.last_active ? new Date(stats.last_active).toLocaleDateString('ru') : '—'}
            valueStyle={{ color: 'var(--foreground)' }}
          />
        </LCard>
      </div>

      {/* Filters */}
      <LCard style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select
            value={selectedSession}
            onChange={e => { setSelectedSession(e.target.value); setViewMode(e.target.value ? 'conversation' : 'list'); }}
            style={{
              flex: 1,
              maxWidth: 300,
              padding: '8px 12px',
              color: 'var(--foreground)',
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              borderRadius: 6,
              fontSize: 14,
            }}
          >
            <option value="">Все сессии</option>
            {sessions.map(s => (
              <option key={s.session_id} value={s.session_id}>
                {sessionLabel(s)}
              </option>
            ))}
          </select>
          <LButton icon={<ReloadOutlined />} onClick={retryHistory}>
            Обновить
          </LButton>
          {selectedSession && (
            <Link
              href={`/ask?session_id=${encodeURIComponent(selectedSession)}`}
              style={{ textDecoration: 'none' }}
            >
              <LButton type="primary">Открыть диалог →</LButton>
            </Link>
          )}
        </div>
      </LCard>

      {/* Content */}
      <LCard>
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 24 }}><LSpin /></div>
        ) : historyIsError ? (
          <LAlert
            type="error"
            showIcon
            message="История недоступна"
            description="Запрос к памяти читателя завершился ошибкой. Фиктивные диалоги не отображаются."
          />
        ) : items.length === 0 ? (
          <LEmpty description="Нет истории вопросов" />
        ) : viewMode === 'list' ? (
          <div>
            {(selectedSession ? items.filter(item => item.role === 'user') : items)
              .map((item) => (
                <div
                  key={item.id}
                  onClick={() => {
                    if (item.session_id) {
                      setSelectedSession(item.session_id);
                      setViewMode('conversation');
                    }
                  }}
                  style={{ padding: '12px 0', borderBottom: '1px solid var(--divider-color)', cursor: item.session_id ? 'pointer' : 'default' }}
                >
                  <div style={{ fontWeight: 500, color: 'var(--foreground)', wordBreak: 'break-word' }}>{item.content}</div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 4 }}>
                    <span style={{ fontSize: 12, color: '#999' }}>{new Date(item.created_at).toLocaleString('ru')}</span>
                    {item.session_id && <span style={{ fontSize: 12, color: '#999' }}>Сессия: {item.session_id.slice(0, 8)}…</span>}
                  </div>
                </div>
              ))}
          </div>
        ) : (
          <div>
            {items.map((item, i) => (
              <div key={i} style={{ padding: '12px 0', borderBottom: '1px solid var(--divider-color)' }}>
                <div style={{ fontWeight: 500, color: item.role === 'user' ? '#1677ff' : '#52c41a', marginBottom: 4 }}>
                  {item.role === 'user' ? 'Вы' : 'Книга'}
                </div>
                <div style={{ color: 'var(--foreground)', wordBreak: 'break-word' }}>{item.content}</div>
                <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                  {new Date(item.created_at).toLocaleString('ru')}
                </div>
              </div>
            ))}
          </div>
        )}
      </LCard>
    </div>
  );
}

export default function HistoryPage() {
  return (
    <ProtectedRoute>
      <HistoryContent />
    </ProtectedRoute>
  );
}

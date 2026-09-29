'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { getReaderHistoryFull } from '@/shared/api/contracts/reader';
import { LCard, LButton, LSpace, LTag, LSpin, LTextArea } from '@/shared/ui/light';
import { SendOutlined, UserOutlined, BulbOutlined, BookOutlined, ArrowRightOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { Markdown } from '@/shared/lib/markdown';
import { ProtectedRoute } from '@/shared/lib/guards';
import { consumeSseResponse } from '@/shared/realtime/sse';
import { SourceBadge } from '@/shared/ui/SourceBadge';
import { EntityCard } from '@/shared/ui/EntityCard';
import Link from 'next/link';
import type { RelatedEntity } from '@/shared/api/contracts/book';

type Message = {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
  time?: string;
  sourceType?: 'pulse' | 'llm' | 'hybrid' | 'mock';
  sessionId?: string;
  relatedEntities?: RelatedEntity[];
};

type ReaderProfile = {
  topics: Array<{ name: string; depth: number; questions: number }>;
  questions_total: number;
  last_topic: string;
};

const POPULAR_QUESTIONS = [
  { q: 'Кто такой Велик?', tag: 'Персонаж' },
  { q: 'Расскажи об Аркаиме', tag: 'Локация' },
  { q: 'Какие темы раскрывает книга?', tag: 'Анализ' },
  { q: 'Что такое Гиперборея?', tag: 'Мифология' },
  { q: 'Какова миссия книги?', tag: 'Философия' },
  { q: 'Какие ценности проповедует книга?', tag: 'Ценности' },
  { q: 'Кто главный герой?', tag: 'Персонаж' },
  { q: 'Где происходит действие?', tag: 'Локация' },
];

function generateSessionId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

function historyTime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });
}

function sourceTypeOf(source?: string): Message['sourceType'] {
  if (!source) return undefined;
  if (source === 'mock') return 'mock';
  if (source.includes('pulse')) return 'pulse';
  return 'llm';
}

function AskContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [restoreState, setRestoreState] = useState<'loading' | 'ok' | 'error'>('loading');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Persistent session ID — survives page reloads within the same conversation
  const [sessionId, setSessionId] = useState(() => {
    const saved = localStorage.getItem('arkaim_session_id');
    return saved || generateSessionId();
  });

  useEffect(() => {
    localStorage.setItem('arkaim_session_id', sessionId);
  }, [sessionId]);

  // A2: resolve session from URL (deep link), then persist it in localStorage
  // and in the URL so Refresh restores the same conversation.
  useEffect(() => {
    let cancelled = false;
    const url = new URL(window.location.href);
    const urlSession = url.searchParams.get('session_id');
    const resolved = urlSession || sessionId;

    if (urlSession && urlSession !== sessionId) {
      setSessionId(urlSession);
      localStorage.setItem('arkaim_session_id', urlSession);
    }
    if (url.searchParams.get('session_id') !== resolved) {
      url.searchParams.set('session_id', resolved);
      window.history.replaceState(null, '', url.toString());
    }

    (async () => {
      try {
        const items = await getReaderHistoryFull({ session_id: resolved, limit: 200 });
        if (cancelled) return;
        if (items.length > 0) {
          const restored: Message[] = items
            .filter(item => item.role === 'user' || item.role === 'assistant')
            .map(item => ({
              role: item.role as 'user' | 'assistant',
              content: item.content,
              time: historyTime(item.created_at),
              sessionId: resolved,
              ...(item.role === 'assistant'
                ? {
                    source: item.metadata?.source,
                    sourceType: sourceTypeOf(item.metadata?.source),
                    relatedEntities: item.metadata?.related_entities,
                  }
                : {}),
            }));
          setMessages(prev => (prev.length > 0 ? prev : restored));
          setRestoreState('ok');
        } else {
          setRestoreState('ok');
        }
      } catch {
        if (!cancelled) setRestoreState('error');
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: profile } = useQuery({
    queryKey: ['reader-profile'],
    queryFn: () => api.get<ReaderProfile>('/book/reader/profile'),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  useEffect(() => {
    if (!sending) inputRef.current?.focus();
  }, [sending]);

  const now = () => new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });

  const sendMessage = useCallback(async (questionText?: string) => {
    const q = (questionText || input).trim();
    if (!q || sending) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q, time: now(), sessionId }]);
    setSending(true);
    setStreamingText('');

    try {
      // arkaim_session — httponly cookie, приходит автоматически (credentials: 'same-origin').
      // Ручной Authorization-заголовок из document.cookie вернул бы ПУСТОЙ токен и
      // перебил бы валидную cookie-сессию в auth.verify_request. Поэтому не шлём его.
      const resp = await fetch('/v1/stream', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: q }],
          metadata: { session_id: sessionId },
        }),
      });

      if (resp.ok && resp.headers.get('content-type')?.includes('text/event-stream')) {
        let fullText = '';
        let relatedEntities: RelatedEntity[] = [];
        await consumeSseResponse(resp, {
          onEvent: ({ data }) => {
            if (typeof data !== 'object' || data === null) return;
            const event = data as { text?: unknown; related_entities?: unknown };
            if (typeof event.text === 'string') {
              fullText += event.text;
              setStreamingText(fullText);
            }
            if (Array.isArray(event.related_entities)) {
              relatedEntities = event.related_entities as RelatedEntity[];
            }
          },
        });
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: fullText || 'Получен пустой ответ.',
          sourceType: 'hybrid',
          time: now(),
          sessionId,
          relatedEntities,
        }]);
      } else {
        const result = await api.post<{ data: { answer: string; source?: string; session_id?: string; related_entities?: RelatedEntity[] } }>('/book/ask', { question: q, session_id: sessionId });
        const sourceType = result.data.source === 'mock' ? 'mock' : result.data.source?.includes('pulse') ? 'pulse' : 'llm';
        setMessages(prev => [...prev, { role: 'assistant', content: result.data.answer, source: result.data.source, sourceType, time: now(), sessionId, relatedEntities: result.data.related_entities }]);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Извините, произошла ошибка. Попробуйте позже.', sourceType: 'mock', time: now(), sessionId }]);
    } finally {
      setSending(false);
      setStreamingText('');
    }
  }, [input, sending, sessionId]);

  const hasHistory = messages.length > 0;

  return (
    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)' }}>
      {!hasHistory && (
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ fontSize: '4rem', marginBottom: 8 }}>𓃉</div>
          <h2 style={{ marginBottom: 8, fontSize: 20, fontWeight: 700 }}>Задайте вопрос книге</h2>
          <span style={{ fontSize: 14, color: '#999' }}>
            Книга ответит на основе своего содержания, тем и знаний
          </span>
          {profile && (
            <div style={{ marginTop: 12 }}>
              <span style={{ fontSize: 12, color: '#999' }}>
                {profile.questions_total} вопросов задано · {profile.topics?.length || 0} тем изучено
              </span>
            </div>
          )}
        </div>
      )}

      {restoreState === 'error' && (
        <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#3f2d1d', border: '1px solid #7c4a1f', color: '#fbbf24', fontSize: 12 }}>
          Не удалось загрузить предыдущие сообщения диалога. Можете продолжить — новый вопрос будет сохранён.
        </div>
      )}

      <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>
        {restoreState === 'loading' ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
            <LSpace><LSpin size="small" /><span style={{ color: '#94a3b8', fontSize: 13 }}>Восстановление диалога...</span></LSpace>
          </div>
        ) : messages.length === 0 ? (
          <div>
            <span style={{ fontSize: 13, marginBottom: 16, display: 'block', color: '#94a3b8' }}>
              <BulbOutlined /> Популярные вопросы:
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
              {POPULAR_QUESTIONS.map((item, i) => (
                <div key={i} style={{ flex: '1 1 calc(50% - 12px)', minWidth: 250 }}>
                  <div
                    onClick={() => sendMessage(item.q)}
                    style={{
                      padding: '14px 18px',
                      background: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: 10,
                      cursor: 'pointer',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = '#3b82f6'; e.currentTarget.style.background = '#253349'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = '#334155'; e.currentTarget.style.background = '#1e293b'; }}
                  >
                    <span style={{ fontSize: 14, color: '#e2e8f0' }}>{item.q}</span>
                    <LSpace size={6}>
                      <LTag style={{ fontSize: 10, margin: 0, background: '#334155', color: '#93c5fd', borderColor: '#475569' }}>{item.tag}</LTag>
                      <ArrowRightOutlined style={{ color: '#64748b', fontSize: 11 }} />
                    </LSpace>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div>
            {messages.map((msg, i) => (
              <div key={i} style={{ marginBottom: 20 }}>
                {msg.role === 'user' ? (
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                    <div style={{ maxWidth: '50%', minWidth: 150, background: '#2563eb', color: '#fff', padding: '12px 16px', borderRadius: '14px 2px 14px 14px', fontSize: 14, lineHeight: 1.6 }}>
                      {msg.content}
                    </div>
                    <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#dbeafe', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <UserOutlined />
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: 10 }}>
                    <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 16 }}>
                      <BookOutlined />
                    </div>
                    <div style={{ maxWidth: '90%' }}>
                      <div style={{
                        background: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '2px 14px 14px 14px',
                        padding: '14px 18px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                      }}>
                        <div style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
                          <Markdown content={msg.content} />
                        </div>
                        {msg.source && (
                          <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid #334155' }}>
                            <SourceBadge sourceType={msg.sourceType} />
                          </div>
                        )}
                      </div>
                      {(msg.relatedEntities?.length ?? 0) > 0 && (
                        <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {msg.relatedEntities!.map(entity => (
                            <EntityCard key={entity.entity_id} entity={entity} sessionId={msg.sessionId} />
                          ))}
                        </div>
                      )}
                      {msg.time && (
                        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, paddingLeft: 4 }}>
                          {msg.time}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {sending && streamingText && (
              <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <BookOutlined />
                </div>
                <div style={{ maxWidth: '80%' }}>
                  <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '2px 14px 14px 14px', padding: '14px 18px', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
                    <div style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.7 }}>
                      <Markdown content={streamingText} />
                      <span style={{ color: '#3b82f6', animation: 'blink 1s infinite' }}>▌</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {sending && !streamingText && (
              <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <BookOutlined />
                </div>
                <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '2px 14px 14px 14px', padding: '14px 18px', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
                  <LSpace><LSpin size="small" /><span style={{ color: '#94a3b8', fontSize: 13 }}>Думаю...</span></LSpace>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <LCard size="small" style={{ borderRadius: 12 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <LTextArea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder={hasHistory ? 'Задайте ещё вопрос...' : 'Ваш вопрос книге...'}
            autoSize={{ minRows: 1, maxRows: 3 }}
            disabled={sending}
            style={{ borderRadius: 8 }}
          />
          <LButton type="primary" icon={<SendOutlined />} onClick={() => sendMessage()} loading={sending}
            style={{ borderRadius: 8, height: 'auto', minWidth: 80 }}>
            Отправить
          </LButton>
        </div>
        <div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 11, color: '#999' }}>Enter — отправить · Shift+Enter — новая строка</span>
          <LSpace size={4}>
            <Link href="/book" style={{ fontSize: 11 }}>💬 Чат</Link>
            <Link href="/library" style={{ fontSize: 11 }}>📖 Библиотека</Link>
          </LSpace>
        </div>
      </LCard>
    </div>
  );
}

export default function AskPage() {
  return (
    <ProtectedRoute>
      <AskContent />
    </ProtectedRoute>
  );
}

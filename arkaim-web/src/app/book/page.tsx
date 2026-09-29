'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { LCard, LButton, LSpace, LTag, LSpin, LProgress, LDrawer, LTextArea, LModal } from '@/shared/ui/light';
import { SendOutlined, UserOutlined, HistoryOutlined, BulbOutlined, ClearOutlined, BookOutlined, MenuOutlined, PlusOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { Markdown } from '@/shared/lib/markdown';
import { ProtectedRoute } from '@/shared/lib/guards';
import { useIsMobile } from '@/shared/lib/hooks';
import { SourceBadge } from '@/shared/ui/SourceBadge';
import Link from 'next/link';

type Message = {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
  time?: string;
  sourceType?: 'pulse' | 'llm' | 'hybrid' | 'mock';
  mood?: 'joy' | 'curiosity' | 'sadness' | 'doubt' | 'deep' | 'neutral';
  suggestion?: string;
};
type HistoryItem = { id: number; content: string; created_at: string };
type HistoryFullItem = { role: 'user' | 'assistant'; content: string; created_at: string };

const EXAMPLE_QUESTIONS = [
  'Кто такой Велик?',
  'Расскажи об Аркаиме',
  'Какие темы раскрывает книга?',
  'Что такое Гиперборея?',
  'Какова миссия книги?',
];

const SESSION_KEY = 'arkaim_chat_session';

function loadSession(): Message[] {
  if (typeof window === 'undefined') return [];
  try { return JSON.parse(localStorage.getItem(SESSION_KEY) || '[]'); } catch { return []; }
}

function saveSession(messages: Message[]) {
  if (typeof window === 'undefined') return;
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(messages.slice(-50))); } catch {}
}

function ChatContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const isMobile = useIsMobile();

  const { data: genome } = useQuery({
    queryKey: ['genome'],
    queryFn: () => api.get<{ themes: Array<{ name: string; description?: string }> }>('/book/genome'),
  });

  const { data: profile } = useQuery({
    queryKey: ['reader-profile'],
    queryFn: () => api.get<{ topics: Array<{ name: string; depth: number; questions: number }>; questions_total: number; conversation_count: number; last_topic: string }>('/book/reader/profile'),
  });

  const { data: historyData } = useQuery({
    queryKey: ['reader-history-preview'],
    queryFn: () => api.get<{ data: HistoryItem[] }>('/book/reader/history?limit=5'),
  });

  const { data: fullHistory } = useQuery({
    queryKey: ['reader-history-full'],
    queryFn: () => api.get<{ data: HistoryFullItem[] }>('/book/reader/history/full?limit=20'),
  });

  const recentQuestions = historyData?.data?.slice(0, 5) || [];

  useEffect(() => {
    const saved = loadSession();
    if (saved.length > 0) setMessages(saved);
  }, []);

  useEffect(() => {
    if (fullHistory?.data && messages.length === 0) {
      setMessages(fullHistory.data.map(item => ({
        role: item.role,
        content: item.content,
        time: new Date(item.created_at).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }),
        sourceType: 'pulse',
      })));
    }
  }, [fullHistory]);

  useEffect(() => { if (messages.length > 0) saveSession(messages); }, [messages]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, streamingText]);
  useEffect(() => { if (!sending) inputRef.current?.focus(); }, [sending]);

  const now = () => new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });

  const sendMessage = useCallback(async (questionText?: string) => {
    const q = (questionText || input).trim();
    if (!q || sending) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q, time: now() }]);
    setSending(true);
    setStreamingText('');

    const dialogueHistory = messages.slice(-6).map(m => ({
      role: m.role,
      content: m.content,
    }));

    try {
      // arkaim_session — httponly cookie, приходит автоматически (credentials: 'same-origin').
      // Ручной Authorization-заголовок из document.cookie вернул бы ПУСТОЙ токен и
      // перебил бы валидную cookie-сессию в auth.verify_request. Поэтому не шлём его.
      const resp = await fetch('/v1/stream', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, messages: dialogueHistory }),
      });

      if (resp.ok && resp.headers.get('content-type')?.includes('text/event-stream')) {
        const reader = resp.body?.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            for (const line of decoder.decode(value, { stream: true }).split('\n')) {
              if (line.startsWith('data: ')) {
                try { const d = JSON.parse(line.slice(6)); if (d.text) { fullText += d.text; setStreamingText(fullText); } } catch {}
              }
            }
          }
        }
        setMessages(prev => [...prev, { role: 'assistant', content: fullText || 'Получен пустой ответ.', sourceType: 'hybrid', time: now() }]);
      } else {
        const result = await api.post<{ data: { answer: string; source?: string; mood?: string; suggestion?: string } }>('/book/ask', { question: q, messages: dialogueHistory });
        const sourceType = result.data.source === 'mock' ? 'mock' : result.data.source?.includes('pulse') ? 'pulse' : 'llm';
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: result.data.answer,
          source: result.data.source,
          sourceType,
          mood: result.data.mood as any,
          suggestion: result.data.suggestion,
          time: now(),
        }]);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Извините, произошла ошибка. Попробуйте позже.', sourceType: 'mock', time: now() }]);
    } finally {
      setSending(false);
      setStreamingText('');
    }
  }, [input, sending, messages]);

  const newSession = () => { setMessages([]); setInput(''); localStorage.removeItem(SESSION_KEY); setConfirmOpen(false); };

  const selectTopic = (topicName: string) => {
    setMessages([]);
    setInput('');
    localStorage.removeItem(SESSION_KEY);
    setTimeout(() => sendMessage(`Расскажи о теме «${topicName}»`), 100);
  };

  const sidebarContent = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <LCard size="small" style={{ background: 'var(--card-bg)', color: 'var(--foreground)', border: '1px solid var(--card-border)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: 4 }}>𓃉</div>
          <span style={{ fontWeight: 600, color: 'var(--foreground)', fontSize: 14 }}>Наследие Аркаима</span>
          <div style={{ color: 'var(--foreground)', opacity: 0.65, fontSize: 12, marginTop: 4 }}>Цифровое сознание книги</div>
          {profile?.last_topic && (
            <div style={{ marginTop: 8 }}>
              <LTag style={{ fontSize: 10, background: 'var(--card-border)', color: 'var(--foreground)', border: '1px solid var(--card-border)' }}>
                Последняя тема: {profile.last_topic}
              </LTag>
            </div>
          )}
        </div>
      </LCard>

      <LCard size="small" title="Навигация">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <Link href="/library" style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--foreground)' }}><BookOutlined /> Библиотека</Link>
          <Link href="/search" style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--foreground)' }}><BulbOutlined /> Поиск</Link>
          <Link href="/reading" style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--foreground)' }}><BookOutlined /> Чтение</Link>
        </div>
      </LCard>

      <LCard size="small" title={<><BookOutlined /> Темы</>}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {genome?.themes?.slice(0, 12).map((t, i) => (
            <LTag
              key={i}
              title={t.description}
              onClick={() => selectTopic(t.name)}
              style={{ marginBottom: 0, cursor: 'pointer', fontSize: 11, background: 'var(--card-border)', color: 'var(--foreground)', borderColor: 'var(--card-border)' }}
            >{t.name}</LTag>
          ))}
        </div>
      </LCard>

      {profile?.topics && profile.topics.length > 0 && (
        <LCard size="small" title="Мои темы">
          {profile.topics.slice(0, 5).map((t, i) => (
            <div key={i} style={{ marginBottom: 6, cursor: 'pointer', padding: '4px 0', borderRadius: 4, transition: 'background 0.2s' }}
              onClick={() => selectTopic(t.name)}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--card-border)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
                <span style={{ color: 'var(--foreground)' }}>{t.name}</span><span style={{ color: 'var(--foreground)', opacity: 0.65, fontSize: 11 }}>{Math.round(t.depth * 100)}%</span>
              </div>
              <LProgress percent={Math.round(t.depth * 100)} size="small" showInfo={false}
                strokeColor={t.depth > 0.7 ? '#52c41a' : t.depth > 0.4 ? '#3b82f6' : 'var(--foreground)'} />
            </div>
          ))}
        </LCard>
      )}

      <LCard size="small">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
            <span style={{ color: 'var(--foreground)', opacity: 0.65 }}>Вопросов</span><span style={{ color: 'var(--foreground)' }}>{profile?.questions_total ?? 0}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
            <span style={{ color: 'var(--foreground)', opacity: 0.65 }}>Диалогов</span><span style={{ color: 'var(--foreground)' }}>{profile?.conversation_count ?? 0}</span>
          </div>
        </div>
      </LCard>
    </div>
  );

  return (
    <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 100px)' }}>
      {!isMobile && <div style={{ width: 260, flexShrink: 0, overflow: 'auto' }}>{sidebarContent}</div>}

      <LDrawer title="Навигация" placement="left" onClose={() => setSidebarOpen(false)} open={sidebarOpen} width={280}>
        {sidebarContent}
      </LDrawer>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <LSpace>
            {isMobile && <LButton type="text" icon={<MenuOutlined />} onClick={() => setSidebarOpen(true)} />}
            <div>
              <h4 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--foreground)' }}>Чат с книгой</h4>
              <span style={{ fontSize: 12, color: 'var(--foreground)', opacity: 0.65 }}>Задайте вопрос книге «Наследие Аркаима»</span>
            </div>
          </LSpace>
          {messages.length > 0 && (
            <LSpace>
              <LButton icon={<PlusOutlined />} size="small" onClick={newSession}>Новая сессия</LButton>
              <LButton icon={<ClearOutlined />} size="small" onClick={() => setConfirmOpen(true)}>Очистить</LButton>
            </LSpace>
          )}
        </div>

        <LModal open={confirmOpen} title="Очистить историю?" onCancel={() => setConfirmOpen(false)}
          footer={<><LButton onClick={() => setConfirmOpen(false)}>Нет</LButton><LButton type="primary" danger onClick={newSession}>Да, очистить</LButton></>}>
          <span>Вы уверены, что хотите очистить всю историю чата?</span>
        </LModal>

        <div style={{ flex: 1, overflow: 'auto', background: 'var(--surface-bg)', borderRadius: 10, padding: 16, border: '1px solid var(--card-border)' }}>
          {messages.length === 0 && (
            <div style={{ padding: '2rem 0', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: 16 }}>𓃉</div>
              <h4 style={{ marginBottom: 8, fontSize: 16, fontWeight: 700, color: 'var(--foreground)' }}>Задайте вопрос книге</h4>
              <span style={{ display: 'block', marginBottom: 24, maxWidth: 400, margin: '0 auto 24px', color: 'var(--foreground)', opacity: 0.65, fontSize: 14 }}>
                Книга ответит на основе своего содержания, тем и знаний
              </span>
              {recentQuestions.length > 0 && (
                <div style={{ marginBottom: 16, maxWidth: 500, margin: '0 auto 16px' }}>
                  <span style={{ fontSize: 12, color: 'var(--foreground)', opacity: 0.65 }}><HistoryOutlined /> Недавние вопросы:</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                    {recentQuestions.map((item, i) => (
                      <div key={i} onClick={() => sendMessage(item.content)}
                        style={{ padding: '10px 14px', background: 'var(--card-border)', border: '1px solid var(--card-border)', borderRadius: 8, cursor: 'pointer', fontSize: 13, textAlign: 'left', color: 'var(--foreground)', transition: 'border-color 0.2s' }}
                        onMouseEnter={e => (e.currentTarget.style.borderColor = '#3b82f6')}
                        onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--card-border)')}>
                        {item.content}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div style={{ maxWidth: 500, margin: '0 auto' }}>
                <span style={{ fontSize: 12, color: 'var(--foreground)', opacity: 0.65 }}><BulbOutlined /> Попробуйте спросить:</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                  {EXAMPLE_QUESTIONS.map((q, i) => (
                    <div key={i} onClick={() => sendMessage(q)}
                      style={{ padding: '10px 14px', background: 'var(--card-border)', border: '1px solid var(--card-border)', borderRadius: 8, cursor: 'pointer', fontSize: 13, textAlign: 'left', color: 'var(--foreground)', transition: 'border-color 0.2s' }}
                      onMouseEnter={e => (e.currentTarget.style.borderColor = '#3b82f6')}
                      onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--card-border)')}>
                      {q}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={{ marginBottom: 16 }}>
              {msg.role === 'user' ? (
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
                  <div style={{ maxWidth: '50%', minWidth: 120, background: '#1677ff', color: '#fff', padding: '10px 14px', borderRadius: '14px 2px 14px 14px', fontSize: 14, lineHeight: 1.6 }}>
                    {msg.content}
                  </div>
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'var(--card-border)', color: '#1677ff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <UserOutlined />
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 10, flex: 1 }}>
                  <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    <BookOutlined />
                  </div>
                  <div style={{ flex: 1, background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '2px 14px 14px 14px', padding: '12px 16px', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
                    <div style={{ color: 'var(--foreground)', fontSize: 14, lineHeight: 1.7 }}>
                      <Markdown content={msg.content} />
                    </div>
                    <SourceBadge sourceType={msg.sourceType} />
                    {msg.time && <div style={{ fontSize: 11, color: 'var(--foreground)', opacity: 0.65, marginTop: 3, paddingLeft: 4 }}>{msg.time}</div>}
                  </div>
                </div>
              )}
            </div>
          ))}

          {sending && streamingText && (
            <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <BookOutlined />
              </div>
              <div style={{ flex: 1, background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '2px 14px 14px 14px', padding: '12px 16px', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
                <div style={{ color: 'var(--foreground)', fontSize: 14, lineHeight: 1.7 }}>
                  <Markdown content={streamingText} />
                  <span style={{ color: '#1677ff' }}>▌</span>
                </div>
              </div>
            </div>
          )}

          {sending && !streamingText && (
            <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <BookOutlined />
              </div>
              <div style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: '2px 14px 14px 14px', padding: '12px 16px', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
                <LSpace><LSpin size="small" /><span style={{ color: 'var(--foreground)', opacity: 0.65, fontSize: 13 }}>Думаю...</span></LSpace>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <LTextArea ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
            onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder={messages.length === 0 ? 'Ваш вопрос книге...' : 'Задайте ещё вопрос...'}
            autoSize={{ minRows: 1, maxRows: 4 }} disabled={sending} style={{ borderRadius: 8 }} />
          <LButton type="primary" icon={<SendOutlined />} onClick={() => sendMessage()} loading={sending}
            style={{ borderRadius: 8, height: 'auto' }}>Отправить</LButton>
        </div>
      </div>
    </div>
  );
}

export default function BookPage() {
  return (
    <ProtectedRoute>
      <ChatContent />
    </ProtectedRoute>
  );
}
'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { getReaderHistoryFull, clearReaderSession } from '@/shared/api/contracts/reader';
import { LCard, LButton, LSpace, LTag, LTextArea, LModal } from '@/shared/ui/light';
import { SendOutlined, UserOutlined, BulbOutlined, BookOutlined, ArrowRightOutlined, DeleteOutlined, RobotOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { Markdown } from '@/shared/lib/markdown';
import { ProtectedRoute } from '@/shared/lib/guards';
import { consumeSseResponse } from '@/shared/realtime/sse';
import { SourceBadge } from '@/shared/ui/SourceBadge';
import { EntityCard } from '@/shared/ui/EntityCard';
import { StateView } from '@/shared/ui/StateView';
import Link from 'next/link';
import type { AskAnswer, RelatedEntity } from '@/shared/api/contracts/book';

type Message = { role: 'user' | 'assistant'; content: string; source?: string; time?: string; pulseConfidence?: number; llmUsed?: boolean; sessionId?: string; relatedEntities?: RelatedEntity[] };
type ReaderProfile = { topics: Array<{ name: string; depth: number; questions: number }>; questions_total: number; last_topic: string };
const POPULAR_QUESTIONS = [
  { q: 'Кто такой Велик?', tag: 'Персонаж' }, { q: 'Расскажи об Аркаиме', tag: 'Локация' },
  { q: 'Какие темы раскрывает книга?', tag: 'Анализ' }, { q: 'Что такое Гиперборея?', tag: 'Мифология' },
  { q: 'Какова миссия книги?', tag: 'Философия' }, { q: 'Какие ценности проповедует книга?', tag: 'Ценности' },
  { q: 'Кто главный герой?', tag: 'Персонаж' }, { q: 'Где происходит действие?', tag: 'Локация' },
];
function generateSessionId(): string { return Math.random().toString(36).substring(2) + Date.now().toString(36); }
function historyTime(iso: string): string { const date = new Date(iso); return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' }); }

function AskContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [restoreState, setRestoreState] = useState<'loading' | 'ok' | 'error'>('loading');
  const [clearOpen, setClearOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearError, setClearError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('arkaim_session_id') || generateSessionId());

  useEffect(() => { localStorage.setItem('arkaim_session_id', sessionId); }, [sessionId]);
  useEffect(() => {
    let cancelled = false;
    const url = new URL(window.location.href);
    const urlSession = url.searchParams.get('session_id');
    const resolved = urlSession || sessionId;
    if (urlSession && urlSession !== sessionId) { setSessionId(urlSession); localStorage.setItem('arkaim_session_id', urlSession); }
    if (url.searchParams.get('session_id') !== resolved) { url.searchParams.set('session_id', resolved); window.history.replaceState(null, '', url.toString()); }
    (async () => {
      try {
        const items = await getReaderHistoryFull({ session_id: resolved, limit: 200 });
        if (cancelled) return;
        const restored: Message[] = items.filter(item => item.role === 'user' || item.role === 'assistant').map(item => ({ role: item.role as 'user' | 'assistant', content: item.content, time: historyTime(item.created_at), sessionId: resolved, ...(item.role === 'assistant' ? { source: item.metadata?.source, relatedEntities: item.metadata?.related_entities } : {}) }));
        setMessages(prev => prev.length > 0 ? prev : restored); setRestoreState('ok');
      } catch { if (!cancelled) setRestoreState('error'); }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: profile } = useQuery({ queryKey: ['reader-profile'], queryFn: () => api.get<ReaderProfile>('/book/reader/profile') });
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, streamingText]);
  useEffect(() => { if (!sending) inputRef.current?.focus(); }, [sending]);
  const now = () => new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });

  const sendMessage = useCallback(async (questionText?: string) => {
    const q = (questionText || input).trim(); if (!q || sending) return;
    setInput(''); setMessages(prev => [...prev, { role: 'user', content: q, time: now(), sessionId }]); setSending(true); setStreamingText('');
    try {
      const resp = await fetch('/v1/stream', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ messages: [{ role: 'user', content: q }], metadata: { session_id: sessionId } }) });
      if (resp.ok && resp.headers.get('content-type')?.includes('text/event-stream')) {
        let fullText = ''; let relatedEntities: RelatedEntity[] = []; let sseSource: string | undefined; let sseConfidence: number | undefined; let sseLlmUsed: boolean | undefined;
        await consumeSseResponse(resp, { onEvent: ({ data }) => { if (typeof data !== 'object' || data === null) return; const event = data as { text?: unknown; related_entities?: unknown; source?: unknown; pulse_confidence?: unknown; llm_used?: unknown }; if (typeof event.text === 'string') { fullText += event.text; setStreamingText(fullText); } if (Array.isArray(event.related_entities)) relatedEntities = event.related_entities as RelatedEntity[]; if (typeof event.source === 'string') sseSource = event.source; if (typeof event.pulse_confidence === 'number') sseConfidence = event.pulse_confidence; if (typeof event.llm_used === 'boolean') sseLlmUsed = event.llm_used; } });
        setMessages(prev => [...prev, { role: 'assistant', content: fullText || 'Получен пустой ответ.', source: sseSource, pulseConfidence: sseConfidence, llmUsed: sseLlmUsed, time: now(), sessionId, relatedEntities }]);
      } else {
        const result = await api.post<{ data: AskAnswer }>('/book/ask', { question: q, session_id: sessionId }); const data = result.data;
        setMessages(prev => [...prev, { role: 'assistant', content: data.answer, source: data.source, pulseConfidence: data.pulse_confidence, llmUsed: data.llm_used, time: now(), sessionId, relatedEntities: data.related_entities }]);
      }
    } catch { setMessages(prev => [...prev, { role: 'assistant', content: 'Извините, произошла ошибка. Попробуйте позже.', time: now(), sessionId }]); }
    finally { setSending(false); setStreamingText(''); }
  }, [input, sending, sessionId]);
  const hasHistory = messages.length > 0;

  const clearCurrentDialog = useCallback(async () => {
    if (clearing) return;
    setClearing(true); setClearError(null);
    try {
      await clearReaderSession(sessionId);
      setMessages([]); setStreamingText(''); setClearOpen(false);
    } catch (e) {
      setClearError(e instanceof Error ? e.message : 'Не удалось очистить диалог');
    } finally { setClearing(false); }
  }, [clearing, sessionId]);

  return <div style={{ width: '100%', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 16 }}>
      <div style={{ fontSize: 12, color: '#94a3b8', lineHeight: 1.6, maxWidth: 720 }}>
        <RobotOutlined style={{ marginRight: 6 }} />
        Ответы формирует ИИ на основе RAG-поиска по проиндексированным знаниям книги: ядро знаний (Pulse) и смысловые слои дополняются языковой моделью там, где готового ответа в книге нет.
        В поиск попадает контекст Читателя — ваши прежние вопросы и темы, — поэтому ответы учитывают ваш контекст чтения.
      </div>
      <LButton icon={<DeleteOutlined />} onClick={() => { setClearError(null); setClearOpen(true); }} disabled={clearing || messages.length === 0} style={{ flexShrink: 0 }}>Очистить</LButton>
    </div>
    {clearError && <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#3f2d1d', border: '1px solid #7c4a1f', color: '#fbbf24', fontSize: 12 }}>{clearError}</div>}
    <LModal open={clearOpen} title="Очистить диалог?" onCancel={() => setClearOpen(false)} footer={<><LButton onClick={() => setClearOpen(false)} disabled={clearing}>Отмена</LButton><LButton type="primary" danger loading={clearing} onClick={clearCurrentDialog}>Очистить</LButton></>}>
      <div style={{ fontSize: 14, color: 'var(--foreground)', lineHeight: 1.7 }}>
        Будут безвозвратно удалены сохранённые сообщения текущего диалога ({sessionId}) — вопросы и ответы в вашей истории.
        Знания книги и ваш профиль Читателя не затрагиваются.
      </div>
    </LModal>
    {!hasHistory && <div style={{ textAlign: 'center', marginBottom: 32 }}><div style={{ fontSize: '4rem', marginBottom: 8 }}>𓃉</div><h2 style={{ marginBottom: 8, fontSize: 20, fontWeight: 700 }}>Задайте вопрос книге</h2><span style={{ fontSize: 14, color: '#999' }}>Книга ответит на основе своего содержания, тем и знаний</span>{profile && <div style={{ marginTop: 12 }}><span style={{ fontSize: 12, color: '#999' }}>{profile.questions_total} вопросов задано · {profile.topics?.length || 0} тем изучено</span></div>}</div>}
    {restoreState === 'error' && <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, background: '#3f2d1d', border: '1px solid #7c4a1f', color: '#fbbf24', fontSize: 12 }}>Не удалось загрузить предыдущие сообщения диалога. Можете продолжить — новый вопрос будет сохранён.</div>}
    <div style={{ flex: 1, overflow: 'auto', marginBottom: 16 }}>{restoreState === 'loading' ? <StateView state="loading" title="Восстановление диалога" description="Загружаем предыдущие сообщения…" /> : messages.length === 0 ? <div><span style={{ fontSize: 13, marginBottom: 16, display: 'block', color: '#94a3b8' }}><BulbOutlined /> Популярные вопросы:</span><div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>{POPULAR_QUESTIONS.map((item, i) => <div key={i} style={{ flex: '1 1 calc(50% - 12px)', minWidth: 250 }}><div onClick={() => sendMessage(item.q)} style={{ padding: '14px 18px', background: '#1e293b', border: '1px solid #334155', borderRadius: 10, cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><span style={{ fontSize: 14, color: '#e2e8f0' }}>{item.q}</span><LSpace size={6}><LTag style={{ fontSize: 10, margin: 0, background: '#334155', color: '#93c5fd', borderColor: '#475569' }}>{item.tag}</LTag><ArrowRightOutlined style={{ color: '#64748b', fontSize: 11 }} /></LSpace></div></div>)}</div></div> : <div>{messages.map((msg, i) => <div key={i} style={{ marginBottom: 20 }}>{msg.role === 'user' ? <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}><div style={{ maxWidth: '50%', minWidth: 150, background: '#2563eb', color: '#fff', padding: '12px 16px', borderRadius: '14px 2px 14px 14px', fontSize: 14, lineHeight: 1.6 }}>{msg.content}</div><div style={{ width: 36, height: 36, borderRadius: '50%', background: '#dbeafe', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}><UserOutlined /></div></div> : <div style={{ display: 'flex', gap: 10 }}><div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 16 }}><BookOutlined /></div><div style={{ maxWidth: '90%' }}><div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '2px 14px 14px 14px', padding: '14px 18px', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}><div style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}><Markdown content={msg.content} /></div>{msg.source && <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid #334155' }}><SourceBadge source={msg.source} confidence={msg.pulseConfidence} llmUsed={msg.llmUsed} /></div>}</div>{(msg.relatedEntities?.length ?? 0) > 0 && <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>{msg.relatedEntities!.map(entity => <EntityCard key={entity.entity_id} entity={entity} sessionId={msg.sessionId} />)}</div>}{msg.time && <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, paddingLeft: 4 }}>{msg.time}</div>}</div></div>}</div>)}{sending && streamingText && <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}><div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}><BookOutlined /></div><div style={{ maxWidth: '80%' }}><div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '2px 14px 14px 14px', padding: '14px 18px' }}><div style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.7 }}><Markdown content={streamingText} /><span style={{ color: '#3b82f6', animation: 'blink 1s infinite' }}>▌</span></div></div></div></div>}{sending && !streamingText && <StateView state="loading" title="Думаю..." style={{ padding: '14px 18px', border: '1px solid #334155', borderRadius: '2px 14px 14px 14px', background: '#1e293b', textAlign: 'left' }} />}<div ref={messagesEndRef} /></div>}</div>
    <LCard size="small" style={{ borderRadius: 12 }}><div style={{ display: 'flex', gap: 8 }}><LTextArea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onPressEnter={e => { if (!e.shiftKey) { e.preventDefault(); sendMessage(); } }} placeholder={hasHistory ? 'Задайте ещё вопрос...' : 'Ваш вопрос книге...'} autoSize={{ minRows: 1, maxRows: 3 }} disabled={sending} style={{ borderRadius: 8 }} /><LButton type="primary" icon={<SendOutlined />} onClick={() => sendMessage()} loading={sending} style={{ borderRadius: 8, height: 'auto', minWidth: 80 }}>Отправить</LButton></div><div style={{ marginTop: 8, display: 'flex', justifyContent: 'space-between' }}><span style={{ fontSize: 11, color: '#999' }}>Enter — отправить · Shift+Enter — новая строка</span><LSpace size={4}><Link href="/book" style={{ fontSize: 11 }}>💬 Чат</Link><Link href="/library" style={{ fontSize: 11 }}>📖 Библиотека</Link></LSpace></div></LCard>
  </div>;
}

export default function AskPage() { return <ProtectedRoute><AskContent /></ProtectedRoute>; }
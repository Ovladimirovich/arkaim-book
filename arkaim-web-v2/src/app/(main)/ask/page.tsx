/**
 * /ask — полноценный streaming-чат с книгой.
 *
 * Контракты (backend):
 *   POST /v1/stream            — SSE streaming (основной канал)
 *   POST /book/ask             — синхрон fallback (редко используется)
 *   GET  /book/reader/history  — история вопросов
 *   GET  /book/reader/profile  — профиль читателя
 *
 * Context transfer из Reading:
 *   /ask?ask=<encodeURIComponent(context)>  — заголовок вопроса из главы
 *
 * Session:
 *   Каждый visit создаёт уникальный UUID через crypto.randomUUID().
 *   Разные вкладки = разные session_id = разные беседы не смешиваются.
 */
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { App, Button, Input, Spin } from 'antd';
import { SendOutlined, ReloadOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { getReaderHistory, getReaderProfile } from '@/shared/api';
import { SourceBadge } from '@/shared/ui/SourceBadge';
import { StateView } from '@/shared/ui/StateView';
import { useStreamingChat } from '@/shared/reading/useStreamingChat';
import type { AskAnswer } from '@/shared/api/contracts/book';

// ── Типы ──────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: AskAnswer;
  time: string;
}

// ── Компонент сообщения ───────────────────────────────────

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user';
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        marginBottom: 16,
        gap: 8,
      }}
    >
      {!isUser && (
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'var(--reading-accent)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 12,
            fontWeight: 700,
            color: '#fff',
            flexShrink: 0,
            marginTop: 2,
          }}
        >
          📖
        </div>
      )}
      <div
        style={{
          maxWidth: '75%',
          background: isUser ? 'var(--reading-active)' : 'var(--reading-surface)',
          border: '1px solid var(--reading-border)',
          borderRadius: 12,
          padding: '10px 14px',
          fontSize: 14,
          lineHeight: 1.6,
          color: 'var(--reading-text)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        <div>{msg.content}</div>
        {!isUser && msg.metadata && (
          <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            <SourceBadge
              source={msg.metadata.source}
              confidence={msg.metadata.pulse_confidence}
              llmUsed={msg.metadata.llm_used}
            />
            {(msg.metadata.provenance ?? []).map((p, i) => (
              <span
                key={i}
                style={{
                  fontSize: 11,
                  color: 'var(--reading-text-secondary)',
                  background: 'var(--reading-hover)',
                  padding: '2px 6px',
                  borderRadius: 4,
                }}
              >
                {p.name ?? p.type}
              </span>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'var(--reading-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 12,
            flexShrink: 0,
            marginTop: 2,
          }}
        >
          👤
        </div>
      )}
    </div>
  );
}

// ── Страница ──────────────────────────────────────────────

export default function AskPage() {
  const { message } = App.useApp();
  const searchParams = useSearchParams();
  const askParam = searchParams.get('ask');

  const [input, setInput] = useState(() => {
    if (askParam) {
      try {
        return decodeURIComponent(askParam);
      } catch {
        return '';
      }
    }
    return '';
  });
  const bottomRef = useRef<HTMLDivElement>(null);

  // Hook manages messages internally; page only tracks input.
  const { text: streamingText, streaming, error: streamError, sendMessage, reset: resetStream, messages: chatMessages } =
    useStreamingChat();

  const profile = useQuery({
    queryKey: ['reader', 'profile'],
    queryFn: () => getReaderProfile(),
    staleTime: 60_000,
  });

  const history = useQuery({
    queryKey: ['reader', 'history'],
    queryFn: () => getReaderHistory(20),
    staleTime: 60_000,
  });

  // Auto-scroll to bottom on new messages or streaming text
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, streamingText]);

  const handleSend = useCallback(async () => {
    const q = input.trim();
    if (!q || streaming) return;
    setInput('');
    try {
      await sendMessage(q, chatMessages);
      void profile.refetch();
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'Ошибка отправки');
    }
  }, [input, streaming, sendMessage, chatMessages, profile, message]);

  const handleNewSession = useCallback(() => {
    resetStream();
    setInput('');
  }, [resetStream]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        void handleSend();
      }
    },
    [handleSend],
  );

  // Build a time-stamped list for rendering
  const renderMessages: ChatMessage[] = chatMessages.map((m, i) => ({
    id: `${m.role}-${i}`,
    role: m.role,
    content: m.content,
    metadata: m.metadata,
    time: new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
  }));

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--reading-bg)',
      }}
    >
      {/* Left: Chat area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          borderRight: '1px solid var(--reading-border)',
        }}
      >
        {/* Header */}
        <header
          style={{
            height: 'var(--reading-topbar-height)',
            borderBottom: '1px solid var(--reading-border)',
            background: 'var(--reading-surface)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 16px',
            gap: 8,
            flexShrink: 0,
          }}
        >
          <Link
            href="/reading"
            style={{
              fontSize: 13,
              color: 'var(--reading-text-secondary)',
              textDecoration: 'none',
              padding: '4px 8px',
              borderRadius: 4,
              border: '1px solid var(--reading-border)',
            }}
          >
            ← Чтение
          </Link>
          <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: 'var(--reading-text)' }}>
            Спросить книгу
          </span>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={handleNewSession}
            disabled={chatMessages.length === 0}
            style={{ fontSize: 12 }}
          >
            Новая сессия
          </Button>
        </header>

        {/* Messages */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px' }}>
          <StateView
            data={renderMessages.length > 0 ? renderMessages : undefined}
            loading={false}
            error={streamError ? { message: streamError } : null}
            empty={!streaming && chatMessages.length === 0}
          >
            {(msgList) => (
              <>
                {msgList.map((msg) => (
                  <MessageBubble key={msg.id} msg={msg} />
                ))}
                {/* Streaming indicator */}
                {streaming && (
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '0 0 8px 36px' }}>
                    <span style={{ fontSize: 12, color: 'var(--reading-text-secondary)' }}>
                      Книга печатает<span className="typing-dots" />
                    </span>
                    <Spin size="small" />
                  </div>
                )}
                <div ref={bottomRef} />
              </>
            )}
          </StateView>
        </div>

        {/* Input */}
        <div
          style={{
            borderTop: '1px solid var(--reading-border)',
            background: 'var(--reading-surface)',
            padding: '12px 16px',
            display: 'flex',
            gap: 8,
            flexShrink: 0,
          }}
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              askParam
                ? 'Ответить на вопрос о главе...'
                : 'Спросить что-нибудь о книге...'
            }
            disabled={streaming}
            allowClear
            style={{ flex: 1 }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={streaming}
            disabled={!input.trim()}
          >
            отправить
          </Button>
        </div>
      </div>

      {/* Right: History sidebar */}
      <aside
        style={{
          width: 280,
          flexShrink: 0,
          background: 'var(--reading-surface)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid var(--reading-border)',
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--reading-text)',
          }}
        >
          История вопросов
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          <StateView
            data={history.data}
            loading={history.isLoading}
            error={history.error instanceof Error ? { message: history.error.message } : null}
            empty={!history.isLoading && (!history.data || history.data.length === 0)}
          >
            {(items) =>
              items.map((item, i) => (
                <div
                  key={item.id}
                  style={{
                    padding: '8px 16px',
                    borderBottom: i < items.length - 1 ? '1px solid var(--reading-border)' : 'none',
                    fontSize: 12,
                    color: 'var(--reading-text-secondary)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={item.content}
                >
                  {item.content}
                </div>
              ))
            }
          </StateView>
        </div>
        {profile.data && (
          <div
            style={{
              padding: '12px 16px',
              borderTop: '1px solid var(--reading-border)',
              fontSize: 12,
              color: 'var(--reading-text-secondary)',
            }}
          >
            Всего вопросов: {profile.data.questions_total}
          </div>
        )}
      </aside>
    </div>
  );
}
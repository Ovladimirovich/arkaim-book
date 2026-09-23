/**
 * / — «Спросить книгу» (F2_SPEC §1). Диалог с книгой.
 *
 * Контракт (live-факт F2):
 *   POST /book/ask → enveloped {data: AskAnswer}
 *     {answer, source, provenance, pulse_confidence, llm_used, mood, suggestion}
 *   messages[] — история диалога (OpenAI-совместимый формат); backend сохраняет контекст.
 *
 * ВНИМАНИЕ: /v1/stream НЕ реализован в бэкенде. Ответ — синхронный (2-5 сек).
 * Стриминг — отдельное улучшение (F4).
 *
 * Инвариант: фронт НЕ синтезирует ответы — только отображает AskAnswer.
 */
'use client';

import { App, Button, Card, Input, List, Spin, Tag, Typography, Avatar } from 'antd';
import { SendOutlined, ReloadOutlined, BulbOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ask, getReaderProfile, ApiError } from '@/shared/api';
import type { AskAnswer } from '@/shared/api/contracts/book';
import { SourceBadge } from '@/shared/ui/SourceBadge';
import { StateView } from '@/shared/ui/StateView';

const { Title, Paragraph, Text } = Typography;

// ── Типы ──────────────────────────────────────────────────

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  source?: AskAnswer;
  time: string;
}

interface TopicItem {
  name: string;
  depth: number;
  questions: number;
}

// ── Популярные вопросы ────────────────────────────────────

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

const MOOD_COLORS: Record<string, string> = {
  curiosity: 'blue',
  intrigue: 'purple',
  reverence: 'gold',
  contemplation: 'cyan',
  conviction: 'green',
};

// ── Куда ещё можно заглянуть (путеводитель по разделам) ──
// Статичный, понятный список основных разделов приложения.
// Помогает сразу понять, ЧТО умеет приложение, а не только чат.
const GUIDE_SECTIONS = [
  { href: '/world', label: 'Модель мира', desc: '547 сущностей вселенной: философия, мифы, география, цивилизации' },
  { href: '/temporal', label: 'Время мира', desc: '12 эпох истории книги и сценарии её будущего' },
  { href: '/library', label: 'Геном книги', desc: 'Темы, персонажи и ценности произведения' },
  { href: '/graph', label: 'Граф знаний', desc: 'Как связаны между собой понятия и факты книги' },
  { href: '/reading', label: 'Чтение', desc: 'Главы книги в режиме чтения' },
  { href: '/profile', label: 'Профиль', desc: 'Ваши темы и история вопросов' },
];

// ── Страница ──────────────────────────────────────────────

export default function AskPage() {
  const { message } = App.useApp();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const profile = useQuery({
    queryKey: ['reader', 'profile'],
    queryFn: () => getReaderProfile(),
    staleTime: 60_000,
  });

  const askMutation = useMutation({
    mutationFn: (q: string) => ask({ question: q }),
    onSuccess: (data) => {
      setError(null);
      // F2_SPEC §6: обновляем профиль после успешного вопроса.
      void profile.refetch();
    },
    onError: (e) => {
      const msg = e instanceof ApiError ? e.message : 'Не удалось получить ответ';
      setError(msg);
      message.error(msg);
    },
  });

  // Автоскролл к последнему сообщению.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, askMutation.isPending]);

  const now = () => new Date().toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' });

  const sendMessage = async (question?: string) => {
    const q = (question ?? input).trim();
    if (!q || askMutation.isPending) return;
    if (q.length < 3) {
      message.warning('Вопрос должен быть не короче 3 символов');
      return;
    }
    setInput('');
    setError(null);

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: q,
      time: now(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const answer = await ask({
        question: q,
        messages: [...messages, userMsg].map((m) => ({ role: m.role, content: m.content })),
      });
      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: answer.answer,
        source: answer,
        time: now(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ошибка запроса';
      setError(msg);
      message.error(msg);
    }
  };

  const handleSend = () => void sendMessage();
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const clearHistory = () => {
    setMessages([]);
    setError(null);
  };

  const lastAssistant = messages.filter((m) => m.role === 'assistant').at(-1);
  const suggestion = lastAssistant?.source?.suggestion;
  const hasMessages = messages.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 800 }}>
      {/* ── Заголовок ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>
            Спросить книгу
          </Title>
          <Paragraph type="secondary" style={{ margin: 4, marginBottom: 0 }}>
            Это живой разговор с книгой «Наследие Аркаима». Задайте любой вопрос о сюжете,
            героях или смыслах — и получите ответ из самой книги, а не из пересказа.
          </Paragraph>
        </div>
        {hasMessages && (
          <Button size="small" icon={<ReloadOutlined />} onClick={clearHistory}>
            Новый диалог
          </Button>
        )}
      </div>

      {/* ── Чат ── */}
      <Card style={{ minHeight: 320, display: 'flex', flexDirection: 'column' }}>
        <StateView
          data={hasMessages ? messages : undefined}
          loading={false}
          error={error ? { message: error } : null}
          empty={!hasMessages}
          onRetry={() => lastAssistant && void sendMessage(lastAssistant.content)}
        >
          {(items) => (
            <List
              dataSource={items}
              renderItem={(msg) => (
                <List.Item
                  style={{
                    flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                    alignItems: 'flex-start',
                    gap: 12,
                  }}
                >
                  <Avatar
                    size={36}
                    style={{
                      backgroundColor: msg.role === 'user' ? '#1677ff' : '#059669',
                      marginTop: 4,
                      flexShrink: 0,
                    }}
                  >
                    {msg.role === 'user' ? 'Вы' : 'К'}
                  </Avatar>
                  <List.Item.Meta
                    title={
                      msg.role === 'assistant' ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <Text strong>Книга</Text>
                          {msg.source && (
                            <SourceBadge
                              source={msg.source.source}
                              confidence={msg.source.pulse_confidence}
                              llmUsed={msg.source.llm_used}
                            />
                          )}
                          {msg.source?.mood && (
                            <span style={{ fontSize: 11 }}>
                              · <Text type="secondary">{msg.source.mood}</Text>
                            </span>
                          )}
                          <Text type="secondary" style={{ fontSize: 11 }}>
                            {msg.time}
                          </Text>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <Text strong>Вы</Text>
                          <Text type="secondary">{msg.time}</Text>
                        </div>
                      )
                    }
                    description={
                      msg.role === 'assistant' ? (
                        <Paragraph
                          style={{
                            whiteSpace: 'pre-wrap',
                            margin: '4px 0 0',
                            fontSize: 15,
                            lineHeight: 1.6,
                          }}
                        >
                          {msg.content}
                        </Paragraph>
                      ) : (
                        <Text style={{ fontSize: 15 }}>{msg.content}</Text>
                      )
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </StateView>

        {/* Спиннер при отправке */}
        {askMutation.isPending && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '16px 8px',
              justifyContent: 'center',
            }}
          >
            <Spin size="small" />
            <Text type="secondary">Книга думает… (ядро Pulse ищет ответ)</Text>
          </div>
        )}
      </Card>

      {/* ── Подсказка следующего вопроса ── */}
      {suggestion && (
        <Card size="small" type="inner" style={{ marginInline: 0 }}>
          <BulbOutlined style={{ color: '#fadb14', marginRight: 8 }} />
          <Text type="secondary">Возможно, стоит спросить: </Text>
          <Button
            type="link"
            style={{ padding: 0, fontSize: 14 }}
            onClick={() => void sendMessage(suggestion)}
            disabled={askMutation.isPending}
          >
            {suggestion}
          </Button>
        </Card>
      )}

      {/* ── Вход ── */}
      <div style={{ display: 'flex', gap: 12 }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Спросить что-нибудь о книге…"
          autoSize={{ minRows: 2, maxRows: 4 }}
          disabled={askMutation.isPending}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleSend}
          loading={askMutation.isPending}
          disabled={!input.trim() || input.trim().length < 3}
          style={{ alignSelf: 'flex-end' }}
        >
          Отправить
        </Button>
      </div>

      {/* ── Популярные вопросы (только если пусто) ── */}
      {!hasMessages && (
        <div>
          <Text type="secondary" style={{ marginBottom: 12, display: 'block' }}>
            Популярные вопросы
          </Text>
          <List
            grid={{ gutter: 12, xs: 1, sm: 1, md: 2, lg: 2 }}
            dataSource={POPULAR_QUESTIONS}
            renderItem={(item) => (
              <List.Item>
                <Card
                  size="small"
                  hoverable
                  onClick={() => void sendMessage(item.q)}
                  style={{ cursor: 'pointer' }}
                >
                  <Tag color="blue" style={{ marginBottom: 4 }}>
                    {item.tag}
                  </Tag>
                  <Paragraph style={{ margin: 0, fontSize: 14 }}>{item.q}</Paragraph>
                </Card>
              </List.Item>
            )}
          />
        </div>
      )}

      {/* ── Путеводитель по разделам (только если пусто) ── */}
      {!hasMessages && (
        <Card title="Куда можно заглянуть ещё" size="small" style={{ marginInline: 0 }}>
          <Paragraph type="secondary" style={{ marginTop: 0 }}>
            Помимо диалога, в приложении есть разделы о мире и смыслах книги. Нажмите, чтобы открыть:
          </Paragraph>
          <List
            grid={{ gutter: 12, xs: 1, sm: 1, md: 2, lg: 2 }}
            dataSource={GUIDE_SECTIONS}
            renderItem={(s) => (
              <List.Item>
                <Link href={s.href} style={{ textDecoration: 'none' }}>
                  <Card size="small" hoverable style={{ cursor: 'pointer' }}>
                    <Text strong>{s.label}</Text>
                    <Paragraph type="secondary" style={{ margin: '4px 0 0', fontSize: 13 }}>
                      {s.desc}
                    </Paragraph>
                  </Card>
                </Link>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* ── Темы профиля ── */}
      <StateView
        data={profile.data}
        loading={profile.isLoading}
        error={(profile.error as ApiError | null) ?? null}
        onRetry={() => void profile.refetch()}
      >
        {(d) =>
          d.topics && d.topics.length > 0 ? (
            <Card title="Ваши темы" size="small">
              <List
                size="small"
                dataSource={d.topics.slice(0, 8)}
                renderItem={(t) => (
                  <List.Item
                    actions={[
                      <Button
                        key="ask"
                        type="link"
                        size="small"
                        onClick={() => void sendMessage(`Расскажи подробнее о теме «${t.name}»`)}
                        disabled={askMutation.isPending}
                      >
                        спросить подробнее
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={t.name}
                      description={`глубина ${t.depth.toFixed(2)} · вопросов: ${t.questions}`}
                    />
                  </List.Item>
                )}
              />
            </Card>
          ) : null
        }
      </StateView>
    </div>
  );
}

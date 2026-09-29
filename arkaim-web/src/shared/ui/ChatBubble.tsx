'use client';

import { UserOutlined, BookOutlined } from '@ant-design/icons';
import { Markdown } from '@/shared/lib/markdown';
import { SourceBadge } from '@/shared/ui/SourceBadge';

type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
  time?: string;
  sourceType?: 'pulse' | 'llm' | 'hybrid' | 'mock';
  mood?: 'joy' | 'curiosity' | 'sadness' | 'doubt' | 'deep' | 'neutral';
  suggestion?: string;
};

const MOOD_CONFIG: Record<string, { emoji: string; color: string; label: string }> = {
  joy: { emoji: '✨', color: '#fbbf24', label: 'Радость' },
  curiosity: { emoji: '🔍', color: '#60a5fa', label: 'Интерес' },
  sadness: { emoji: '🌙', color: '#a78bfa', label: 'Глубина' },
  doubt: { emoji: '💭', color: '#94a3b8', label: 'Размышление' },
  deep: { emoji: '🌊', color: '#34d399', label: 'Мудрость' },
  neutral: { emoji: '', color: '', label: '' },
};

export function ChatBubble({ msg }: { msg: ChatMessage }) {
  if (msg.role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
        <div style={{ maxWidth: '50%', minWidth: 150, background: '#2563eb', color: '#fff', padding: '12px 16px', borderRadius: '14px 2px 14px 14px', fontSize: 14, lineHeight: 1.6 }}>
          {msg.content}
        </div>
        <div style={{ width: 36, height: 36, borderRadius: '50%', background: '#dbeafe', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <UserOutlined />
        </div>
      </div>
    );
  }

  const moodConfig = msg.mood ? MOOD_CONFIG[msg.mood] : MOOD_CONFIG.neutral;

  return (
    <div style={{ display: 'flex', gap: 10 }}>
      <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, fontSize: 16 }}>
        <BookOutlined />
      </div>
      <div style={{ maxWidth: '90%' }}>
        <div style={{
          background: '#1e293b',
          border: `1px solid ${moodConfig.color || '#334155'}`,
          borderRadius: '2px 14px 14px 14px',
          padding: '14px 18px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
        }}>
          {moodConfig.emoji && (
            <div style={{ fontSize: 11, color: moodConfig.color, marginBottom: 6 }}>
              {moodConfig.emoji} {moodConfig.label}
            </div>
          )}
          <div style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
            <Markdown content={msg.content} />
          </div>
          {msg.suggestion && (
            <div style={{ marginTop: 10, padding: '8px 12px', background: '#0f172a', borderRadius: 6, borderLeft: '3px solid #3b82f6' }}>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>💡 {msg.suggestion}</div>
            </div>
          )}
          {msg.source && (
            <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid #334155' }}>
              <SourceBadge sourceType={msg.sourceType} />
            </div>
          )}
        </div>
        {msg.time && (
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4, paddingLeft: 4 }}>
            {msg.time}
          </div>
        )}
      </div>
    </div>
  );
}

export function StreamingBubble({ text }: { text: string }) {
  return (
    <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
      <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg, #0f172a, #1e293b)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <BookOutlined />
      </div>
      <div style={{ maxWidth: '80%' }}>
        <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '2px 14px 14px 14px', padding: '14px 18px', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
          <div style={{ color: '#e2e8f0', fontSize: 14, lineHeight: 1.7 }}>
            <Markdown content={text} />
            <span style={{ display: 'inline-block', width: 8, height: 16, background: '#e2e8f0', marginLeft: 2, animation: 'blink 1s infinite' }} />
          </div>
        </div>
      </div>
    </div>
  );
}

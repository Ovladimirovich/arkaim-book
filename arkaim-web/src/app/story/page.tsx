'use client';

import { useState, useCallback, useRef } from 'react';
import { ThunderboltOutlined, SendOutlined, GlobalOutlined, ExperimentOutlined, CheckCircleOutlined, WarningOutlined, BookOutlined, EnvironmentOutlined, TeamOutlined, ToolOutlined, SafetyCertificateOutlined, LoadingOutlined } from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { Markdown } from '@/shared/lib/markdown';
import { LCard } from '@/shared/ui/light/LCard';
import { LTag } from '@/shared/ui/light/LTag';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LAlert } from '@/shared/ui/light/LAlert';
import { LBadge } from '@/shared/ui/light/LBadge';

type WorldModel = {
  epochs: Array<{ id: string; name: string; name_ru: string; description: string; order: number }>;
  locations: Array<{ id: string; name: string; name_ru: string; type: string; description: string }>;
  canonical_events: Array<{ id: string; title_ru: string; epoch: string }>;
  causal_rules: Array<{ id: string; description: string; rule_type: string }>;
};

type ConstraintModel = {
  story_request: { prompt: string; epoch?: string; location?: string; character_type?: string };
  resolved_context: {
    epoch?: { name_ru: string; description: string };
    location?: { name_ru: string; description: string };
    characters_alive: Array<{ character_name: string; status: string }>;
    technologies_available: Array<{ name_ru: string }>;
    applicable_rules: Array<{ description: string }>;
  };
  hard_constraints: string[];
  soft_constraints: string[];
  forbidden_elements: string[];
};

type StoryResult = {
  id: string;
  text: string;
  word_count: number;
  constraints: ConstraintModel;
  validation: { passed: boolean; violations: { rule: string; rule_text?: string; message: string }[]; warnings: string[] };
};

const STORY_PRESETS = [
  { label: '30 лет до Велика', prompt: 'Я хочу историю о молодом гиперборейце за 30 лет до появления Велика.' },
  { label: 'День гиперборейца', prompt: 'Покажи один день из жизни гиперборейца в Сатья Юге.' },
  { label: 'Основание Аркаима', prompt: 'История о том, как был основан Аркаим.' },
  { label: 'Ритуал жреца', prompt: 'Расскажи о ритуале, который проводил жрец в храме огня.' },
  { label: 'Путешественник', prompt: 'История о страннике, пересекающем земли от Гипербореи до Индии.' },
  { label: 'Последний учитель', prompt: 'О последнем учителе, который уходил из умирающего города.' },
];

function ConstraintDisplay({ constraints }: { constraints: ConstraintModel }) {
  const ctx = constraints.resolved_context;
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({ epoch: true, rules: true });

  const toggle = (key: string) => setOpenSections(prev => ({ ...prev, [key]: !prev[key] }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* Epoch */}
      <LCard size="small">
        <div onClick={() => toggle('epoch')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
          <GlobalOutlined /> <strong>Эпоха</strong>
          {ctx.epoch && <LTag color="blue">{ctx.epoch.name_ru}</LTag>}
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#999' }}>{openSections.epoch ? '▲' : '▼'}</span>
        </div>
        {openSections.epoch && ctx.epoch && (
          <div style={{ marginTop: 8 }}>
            <p>{ctx.epoch.description}</p>
            {ctx.characters_alive.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <strong>Персонажи в эпохе:</strong>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                  {ctx.characters_alive.map((ch, i) => (
                    <LTag key={i} color="blue"><TeamOutlined /> {ch.character_name} ({ch.status})</LTag>
                  ))}
                </div>
              </div>
            )}
            {ctx.technologies_available.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <strong>Технологии:</strong>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                  {ctx.technologies_available.map((t, i) => (
                    <LTag key={i} color="green"><ToolOutlined /> {t.name_ru}</LTag>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </LCard>

      {/* Location */}
      <LCard size="small">
        <div onClick={() => toggle('location')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
          <EnvironmentOutlined /> <strong>Локация</strong>
          {ctx.location && <LTag color="green">{ctx.location.name_ru}</LTag>}
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#999' }}>{openSections.location ? '▲' : '▼'}</span>
        </div>
        {openSections.location && ctx.location && (
          <div style={{ marginTop: 8 }}><p>{ctx.location.description}</p></div>
        )}
      </LCard>

      {/* Rules */}
      <LCard size="small">
        <div onClick={() => toggle('rules')} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
          <SafetyCertificateOutlined /> <strong>Ограничения</strong>
          <LBadge count={constraints.hard_constraints.length} color="#ff4d4f" />
          <span style={{ marginLeft: 'auto', fontSize: 12, color: '#999' }}>{openSections.rules ? '▲' : '▼'}</span>
        </div>
        {openSections.rules && (
          <div style={{ marginTop: 8 }}>
            <strong>Жёсткие ограничения:</strong>
            {constraints.hard_constraints.map((item, i) => (
              <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid var(--divider-color)' }}>
                <LTag color="red">MUST</LTag> {item}
              </div>
            ))}
            {constraints.forbidden_elements.length > 0 && (
              <div style={{ marginTop: 8 }}>
                <strong style={{ color: '#ff4d4f' }}>Запрещено:</strong>
                {constraints.forbidden_elements.map((item, i) => (
                  <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid var(--divider-color)' }}>
                    <LTag color="orange">NO</LTag> {item}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </LCard>
    </div>
  );
}

function StoryOutput({ story, streamingText, isStreaming }: {
  story: StoryResult | null;
  streamingText: string;
  isStreaming: boolean;
}) {
  if (isStreaming && streamingText) {
    return (
      <LCard title={<span><BookOutlined /> Генерация... <LoadingOutlined /></span>}>
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          <Markdown content={streamingText} />
          <span style={{ animation: 'blink 1s infinite' }}>|</span>
        </div>
      </LCard>
    );
  }

  if (!story) return null;

  return (
    <LCard
      title={<span><BookOutlined /> Сгенерированная история <LTag>{story.word_count} слов</LTag></span>}
      extra={story.validation.passed ? (
        <LTag color="green"><CheckCircleOutlined /> Валидация пройдена</LTag>
      ) : (
        <LTag color="red"><WarningOutlined /> Есть нарушения</LTag>
      )}
    >
      <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
        <Markdown content={story.text} />
      </div>
      {story.validation.warnings.length > 0 && (
        <LAlert type="warning" message="Предупреждения" style={{ marginTop: 16 }} />
      )}
      {story.validation.violations.length > 0 && (
        <LAlert type="error" message="Нарушения ограничений" style={{ marginTop: 8 }} />
      )}
    </LCard>
  );
}

function WorldModelPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['world-model'],
    queryFn: () => api.get<{ data: WorldModel }>('/book/world-engine/model'),
  });

  if (isLoading) return <LSpin size="small" />;
  const wm = data?.data;
  if (!wm) return <LEmpty description="Модель мира не загружена" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <LCard size="small" title="Эпохи">
        {wm.epochs.map(ep => (
          <div key={ep.id} style={{ padding: '4px 0', borderBottom: '1px solid var(--divider-color)', fontSize: 13 }}>
            {ep.name_ru || ep.name}
          </div>
        ))}
      </LCard>
      <LCard size="small" title="Локации">
        {wm.locations.map(loc => (
          <div key={loc.id} style={{ padding: '4px 0', borderBottom: '1px solid var(--divider-color)', fontSize: 13, display: 'flex', justifyContent: 'space-between' }}>
            <span>{loc.name_ru || loc.name}</span>
            <LTag>{loc.type}</LTag>
          </div>
        ))}
      </LCard>
    </div>
  );
}

function StoryPageContent() {
  const [prompt, setPrompt] = useState('');
  const [constraints, setConstraints] = useState<ConstraintModel | null>(null);
  const [story, setStory] = useState<StoryResult | null>(null);
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingTextRef = useRef('');

  const constraintsMutation = useMutation({
    mutationFn: (req: { prompt: string }) =>
      api.post<{ data: ConstraintModel }>('/book/story-engine/constraints', req),
    onSuccess: (data) => setConstraints(data.data),
  });

  const handleParse = useCallback(() => {
    if (!prompt.trim()) return;
    constraintsMutation.mutate({ prompt });
  }, [prompt, constraintsMutation]);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || isStreaming) return;

    setIsStreaming(true);
    setStreamingText('');
    streamingTextRef.current = '';
    setStory(null);

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/book/story-engine/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, style: 'literary' }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'chunk') {
                streamingTextRef.current += parsed.text;
                setStreamingText(streamingTextRef.current);
              } else if (parsed.type === 'done') {
                setStory({
                  id: parsed.id,
                  text: streamingTextRef.current,
                  word_count: parsed.word_count,
                  constraints: constraints!,
                  validation: parsed.validation,
                });
                streamingTextRef.current = '';
              } else if (parsed.type === 'constraints') {
                setConstraints(parsed.data);
              }
            } catch {}
          }
        }
      }
    } catch (err: unknown) {
      const error = err as { name?: string };
      if (error.name !== 'AbortError') {
        // Silent error
      }
    } finally {
      setIsStreaming(false);
    }
  }, [prompt, isStreaming, constraints]);

  const handlePreset = useCallback((presetPrompt: string) => {
    setPrompt(presetPrompt);
    constraintsMutation.mutate({ prompt: presetPrompt });
  }, [constraintsMutation]);

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 48px)' }}>
      {/* Sidebar */}
      <div style={{ width: 280, borderRight: '1px solid #f0f0f0', padding: 16, overflow: 'auto', flexShrink: 0 }}>
        <h5 style={{ marginBottom: 16 }}><ThunderboltOutlined /> Пресеты</h5>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {STORY_PRESETS.map((preset, i) => (
            <LButton key={i} onClick={() => handlePreset(preset.prompt)} style={{ textAlign: 'left', height: 'auto', padding: '8px 12px', width: '100%' }}>
              {preset.label}
            </LButton>
          ))}
        </div>

        <h5 style={{ marginTop: 24, marginBottom: 16 }}><GlobalOutlined /> Мир</h5>
        <WorldModelPanel />
      </div>

      {/* Main */}
      <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
        <h2><ThunderboltOutlined /> Движок Повествования</h2>
        <p style={{ color: '#999' }}>
          Создавайте истории внутри мира книги. Сначала система строит модель ограничений, затем LLM пишет внутри них.
        </p>

        {/* Input */}
        <LCard style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <textarea
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              placeholder={'Опишите историю, которую хотите создать...\nНапример: «Я хочу историю о молодом гиперборейце за 30 лет до появления Велика»'}
              rows={4}
              style={{ width: '100%', padding: 12, border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 14, resize: 'vertical' }}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <LButton type="primary" icon={<ExperimentOutlined />} onClick={handleParse} loading={constraintsMutation.isPending}>
                Построить ограничения
              </LButton>
              <LButton icon={isStreaming ? <LoadingOutlined /> : <SendOutlined />} onClick={handleGenerate} disabled={!constraints && !isStreaming}>
                {isStreaming ? 'Генерация...' : 'Сгенерировать историю'}
              </LButton>
              {isStreaming && (
                <LButton danger onClick={() => abortControllerRef.current?.abort()}>
                  Стоп
                </LButton>
              )}
            </div>
          </div>
        </LCard>

        {/* Constraints */}
        {constraints && (
          <div style={{ marginBottom: 24 }}>
            <h4>Модель ограничений</h4>
            <ConstraintDisplay constraints={constraints} />
          </div>
        )}

        {/* Story Output */}
        <StoryOutput story={story} streamingText={streamingText} isStreaming={isStreaming} />

        {/* Loading */}
        {constraintsMutation.isPending && (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <LSpin size="large" tip="Анализ мира..." />
          </div>
        )}
      </div>

      <style jsx global>{`
        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
}

export default function StoryPage() {
  return (
    <ProtectedRoute>
      <StoryPageContent />
    </ProtectedRoute>
  );
}

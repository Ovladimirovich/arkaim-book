'use client';

import { useState, useEffect, useRef } from 'react';
import { VideoCameraOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LDivider } from '@/shared/ui/light/LDivider';

type SceneMeta = {
  id: string;
  title: string;
  char_count: number;
  index: number;
};

type SceneFull = SceneMeta & {
  content: string;
};

const FONT_SIZES = [
  { label: 'Маленький', value: 14 },
  { label: 'Средний', value: 16 },
  { label: 'Большой', value: 18 },
];

function SceneView({ scene, fontSize }: { scene: SceneFull; fontSize: number }) {
  const lines = scene.content.split('\n');
  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h3 style={{ marginBottom: 24, textAlign: 'center' }}>
        <VideoCameraOutlined style={{ marginRight: 8, color: '#dc2626' }} />
        {scene.title}
      </h3>
      <LDivider />
      <div style={{ fontSize, lineHeight: 1.8, color: '#374151' }}>
        {lines.map((line, i) => {
          const trimmed = line.trim();
          if (!trimmed) return <div key={i} style={{ height: '0.8em' }} />;
          if (trimmed.startsWith('(') && trimmed.endsWith(')')) {
            return <p key={i} style={{ fontSize, fontStyle: 'italic', color: '#6b7280', marginBottom: '0.6em' }}>{trimmed}</p>;
          }
          if (/^[А-ЯЁ\s-]+$/.test(trimmed) && trimmed.length < 40) {
            return <p key={i} style={{ fontSize, fontWeight: 700, textAlign: 'center', marginTop: '1em', marginBottom: '0.3em' }}>{trimmed}</p>;
          }
          if (trimmed.startsWith('-')) {
            return <p key={i} style={{ fontSize, marginLeft: '2em', marginBottom: '0.6em' }}>{trimmed}</p>;
          }
          return <p key={i} style={{ fontSize, marginBottom: '0.6em' }}>{trimmed}</p>;
        })}
      </div>
      <LDivider />
      <div style={{ textAlign: 'center' }}>
        <span style={{ fontSize: 12, color: '#999' }}>Конец сцены</span>
      </div>
    </div>
  );
}

function ScreenplayContent() {
  const [sceneIndex, setSceneIndex] = useState(0);
  const [fontSize, setFontSize] = useState(16);
  const [showToc, setShowToc] = useState(true);
  const contentRef = useRef<HTMLDivElement>(null);

  const { data: scenesData, isLoading: scenesLoading } = useQuery({
    queryKey: ['screenplay-scenes'],
    queryFn: () => api.get<{ ok: boolean; data: SceneMeta[]; total: number }>('/book/screenplay'),
  });

  const scenes: SceneMeta[] = scenesData?.data || [];
  const currentScene = scenes[sceneIndex];

  const { data: sceneData, isLoading: sceneLoading } = useQuery({
    queryKey: ['screenplay-scene', currentScene?.id],
    queryFn: () => api.get<{ ok: boolean; data: SceneFull }>(`/book/screenplay/${currentScene?.id}`),
    enabled: !!currentScene?.id,
  });

  const sceneContent: SceneFull | undefined = sceneData?.data;

  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [sceneIndex]);

  const prevScene = () => { if (sceneIndex > 0) setSceneIndex(sceneIndex - 1); };
  const nextScene = () => { if (sceneIndex < scenes.length - 1) setSceneIndex(sceneIndex + 1); };

  if (scenesLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <LSpin size="large" tip="Загрузка сценария..." />
      </div>
    );
  }

  if (scenes.length === 0) {
    return <LEmpty description="Сценарий не найден" />;
  }

  return (
    <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 100px)' }}>
      {showToc && (
        <div style={{ width: 280, flexShrink: 0, overflow: 'auto' }}>
          <LCard size="small" title={<span><VideoCameraOutlined /> Сцены</span>} extra={<span style={{ fontSize: 12, color: '#999' }}>{scenes.length}</span>}>
            {scenes.map((item, i) => (
              <div
                key={item.id}
                onClick={() => setSceneIndex(i)}
                style={{
                  cursor: 'pointer',
                  background: i === sceneIndex ? '#fef2f2' : undefined,
                  borderRadius: 4,
                  padding: '6px 8px',
                  fontSize: 11,
                  color: i === sceneIndex ? '#dc2626' : undefined,
                }}
              >
                {item.title}
              </div>
            ))}
          </LCard>
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <LButton size="small" onClick={() => setShowToc(!showToc)}>
            {showToc ? 'Скрыть' : 'Сцены'}
          </LButton>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12, color: '#999' }}>Шрифт:</span>
            <div style={{ display: 'flex', border: '1px solid var(--input-border)', borderRadius: 6, overflow: 'hidden' }}>
              {FONT_SIZES.map(f => (
                <button
                  key={f.value}
                  onClick={() => setFontSize(f.value)}
                  style={{
                    padding: '4px 10px',
                    fontSize: 12,
                    border: 'none',
                    background: fontSize === f.value ? '#1677ff' : 'var(--surface-bg)',
                    color: fontSize === f.value ? '#fff' : '#333',
                    cursor: 'pointer',
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div ref={contentRef} style={{ flex: 1, overflow: 'auto' }}>
        <LCard size="small" style={{ height: '100%' }}>
          {sceneLoading ? (
            <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
          ) : sceneContent ? (
            <SceneView scene={sceneContent} fontSize={fontSize} />
          ) : (
            <LEmpty description="Сцена не найдена" />
          )}
        </LCard>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
          <LButton icon={<LeftOutlined />} onClick={prevScene} disabled={sceneIndex === 0}>
            Предыдущая
          </LButton>
          <span style={{ fontSize: 12, color: '#999' }}>
            {sceneIndex + 1} / {scenes.length}
          </span>
          <LButton onClick={nextScene} disabled={sceneIndex === scenes.length - 1}>
            Следующая <RightOutlined />
          </LButton>
        </div>
      </div>
    </div>
  );
}

export default function ScreenplayPage() {
  return (
    <ProtectedRoute>
      <ScreenplayContent />
    </ProtectedRoute>
  );
}

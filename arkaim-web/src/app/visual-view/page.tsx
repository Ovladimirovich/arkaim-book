'use client';

import React, { useState, Suspense, lazy } from 'react';

// ── VisualContext Generator ──────────────────────────
// ComfyUI Generate Button for Scene Cards
function GenerateSceneButton({ chapter, sceneId }: { chapter: number; sceneId: string }) {
  const mutation = useGenerateImage();
  const [result, setResult] = React.useState<any>(null);

  return (
    <div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          setResult(null);
          mutation.mutate({ chapter, scene_id: sceneId }, {
            onSuccess: (data) => { setResult(data); },
          });
        }}
        disabled={mutation.isPending}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '2px 8px', fontSize: 11, borderRadius: 4,
          border: '1px solid var(--input-border)', background: 'var(--surface-bg)', cursor: mutation.isPending ? 'wait' : 'pointer',
          color: mutation.isError ? '#ef4444' : '#2563eb',
        }}
        title={mutation.isError ? String(mutation.error) : 'Сгенерировать изображение через ComfyUI'}
      >
        {mutation.isPending ? <LoadingOutlined /> : <ThunderboltOutlined />}
        {mutation.isPending ? 'Генерация...' : 'Сгенерировать'}
      </button>
      {mutation.isError && (
        <div style={{ fontSize: 10, color: '#ef4444', marginTop: 4 }}>{String(mutation.error)}</div>
      )}
      {result?.data?.file_path && (
        <div style={{ marginTop: 8 }}>
          <img
            src={`/book/assets/${result.data.id}/file`}
            alt={sceneId}
            loading="lazy"
            style={{ maxWidth: '100%', borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          <div style={{ fontSize: 10, color: '#666', marginTop: 4 }}>
            {result.data.provider || 'comfyui'}
          </div>
        </div>
      )}
    </div>
  );
}


function VisualContextGenerator() {
  const settings = useGenerationSettings();
  const [entityId, setEntityId] = React.useState("");
  const [prompt, setPrompt] = React.useState("");
  const generate = async () => {
    const res = await fetch(`/book/world/entity/${entityId}/visual-prompt?style=${settings.style}`);
    const data = await res.json();
    setPrompt(data.prompt || "Error");
  };
  return (
    <div style={{ padding: 16, border: '1px solid var(--card-border)', borderRadius: 8, marginBottom: 16 }}>
      <h3>Генерация из VisualContext</h3>
      <input value={entityId} onChange={e => setEntityId(e.target.value)} placeholder="ID сущности" style={{ width: 300, marginRight: 8 }} />
      <button onClick={generate}>Генерировать</button>
      {prompt && <pre style={{ marginTop: 16, padding: 16, background: 'var(--surface-bg)', borderRadius: 8 }}>{prompt}</pre>}
    </div>
  );
}


// useState already imported above
import { LCard, LTag, LTabs, LEmpty, LSpin, LSpace, LInput, LModal, LButton, LDivider, LAvatar } from '@/shared/ui/light';
import { PictureOutlined, TeamOutlined, EnvironmentOutlined, SearchOutlined, EyeOutlined, BookOutlined, BulbOutlined, BgColorsOutlined, ThunderboltOutlined, LoadingOutlined, SettingOutlined } from '@ant-design/icons';
import { ComfyUIStatus } from '@/shared/ui/ComfyUIStatus';
const GenerationSettingsPanel = lazy(() => import('@/shared/ui/GenerationSettingsPanel').then(m => ({ default: m.GenerationSettingsPanel })));
import { useGenerateImage } from '@/shared/lib/useGenerateImage';
import { useGenerationSettings } from '@/shared/contexts/GenerationSettingsContext';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';

type GenomeData = {
  modules?: {
    scenes?: Array<{ chapter: number; scene_id: string; title: string; characters: string[]; location: string; emotion: string; meaning_tags: string[]; color_palette?: string[]; source?: string }>;
    character_visuals?: Array<{ character_id: string; name: string; archetype?: string; visual_description: string; color_palette: string[] }>;
    location_visuals?: Array<{ location_id: string; name: string; atmosphere?: string; architecture?: string; lighting?: string }>;
  };
  themes?: Array<{ name: string; description?: string }>;
  characters?: Array<{ id: string; name: string; role?: string; description?: string }>;
  world_entities?: Array<{ id: string; name: string; type?: string }>;
};

const EMOTION_COLORS: Record<string, string> = {
  neutral: '#6b7280', joy: '#f59e0b', sadness: '#3b82f6', anger: '#ef4444',
  fear: '#8b5cf6', surprise: '#10b981', mystery: '#6366f1',
};

// ── Scenes Gallery ──────────────────────────────────

function ScenesGallery({ genome, isLoading }: { genome?: GenomeData; isLoading: boolean }) {
  const [search, setSearch] = useState('');
  const [selectedScene, setSelectedScene] = useState<any>(null);

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;

  const scenes = (genome?.modules?.scenes || [])
    .filter(s => !search || s.title.toLowerCase().includes(search.toLowerCase()) ||
      s.characters?.some(c => c.toLowerCase().includes(search.toLowerCase())) ||
      s.location?.toLowerCase().includes(search.toLowerCase()));

  if (scenes.length === 0) return <LEmpty description="Сцены не найдены" />;

  // Группировка по главам
  const chapters = scenes.reduce((acc, scene) => {
    const ch = scene.chapter || 0;
    if (!acc[ch]) acc[ch] = [];
    acc[ch].push(scene);
    return acc;
  }, {} as Record<number, typeof scenes>);

  return (
    <div>
      <LInput
        prefix={<SearchOutlined />}
        placeholder="Поиск по сценам..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        allowClear
        style={{ marginBottom: 16, maxWidth: 400 }}
      />

      {Object.entries(chapters).sort(([a], [b]) => Number(a) - Number(b)).map(([chapter, chScenes]) => (
        <div key={chapter} style={{ marginBottom: 24 }}>
          <h4 style={{ marginBottom: 12 }}>
            <BookOutlined style={{ marginRight: 8, color: '#2563eb' }} />
            Глава {chapter}
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {chScenes.map((scene, i) => (
              <LCard
                key={scene.scene_id || i}
                hoverable
                size="small"
                onClick={() => setSelectedScene(scene)}
                style={{ height: '100%', borderLeft: `3px solid ${EMOTION_COLORS[scene.emotion] || '#6b7280'}` }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                  <strong style={{ fontSize: 14 }}>{scene.title}</strong>
                  <LTag color={EMOTION_COLORS[scene.emotion] ? undefined : 'default'}
                    style={{ background: EMOTION_COLORS[scene.emotion] || '#6b7280', color: '#fff', border: 'none', fontSize: 10 }}>
                    {scene.emotion}
                  </LTag>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 2, width: '100%' }}>
                  {scene.characters?.length > 0 && (
                    <div style={{ fontSize: 12, color: '#666' }}>
                      <TeamOutlined style={{ marginRight: 4 }} />
                      {scene.characters.join(', ')}
                    </div>
                  )}
                  {scene.location && (
                    <div style={{ fontSize: 12, color: '#666' }}>
                      <EnvironmentOutlined style={{ marginRight: 4 }} />
                      {scene.location}
                    </div>
                  )}
                </div>

                {scene.meaning_tags?.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {scene.meaning_tags.slice(0, 3).map((t: string, j: number) => (
                      <LTag key={j} style={{ fontSize: 10, margin: 0 }}>{t}</LTag>
                    ))}
                  </div>
                )}

                <div style={{ marginTop: 8 }}>
                  <GenerateSceneButton chapter={scene.chapter} sceneId={scene.scene_id} />
                </div>
              </LCard>
            ))}
          </div>
        </div>
      ))}

      <LModal
        title={<LSpace><EyeOutlined /> {selectedScene?.title}</LSpace>}
        open={!!selectedScene}
        onCancel={() => setSelectedScene(null)}
        footer={null}
        width={600}
      >
        {selectedScene && (
          <div>
            <div style={{ textAlign: 'center', padding: '24px 0', background: 'var(--surface-bg)', borderRadius: 8, marginBottom: 16 }}>
              <div style={{ fontSize: 48, marginBottom: 8 }}>🎭</div>
              <h3 style={{ margin: 0 }}>{selectedScene.title}</h3>
              <LTag style={{ marginTop: 8, background: EMOTION_COLORS[selectedScene.emotion] || '#6b7280', color: '#fff', border: 'none' }}>
                {selectedScene.emotion}
              </LTag>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div><strong>Глава:</strong> {selectedScene.chapter}</div>
              <div><strong>Сцена ID:</strong> <code>{selectedScene.scene_id}</code></div>
              <div><strong>Персонажи:</strong> {selectedScene.characters?.map((c: string, i: number) => <LTag key={i} icon={<TeamOutlined />}>{c}</LTag>) || '—'}</div>
              <div><strong>Локация:</strong> {selectedScene.location ? <LTag icon={<EnvironmentOutlined />}>{selectedScene.location}</LTag> : '—'}</div>
              <div><strong>Теги смысла:</strong> {selectedScene.meaning_tags?.map((t: string, i: number) => <LTag key={i} color="purple">{t}</LTag>) || '—'}</div>
              {selectedScene.color_palette?.length > 0 && (
                <div><strong>Палитра:</strong>
                  <LSpace>
                    {selectedScene.color_palette.map((c: string, i: number) => (
                      <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span style={{ width: 24, height: 24, borderRadius: 4, background: c, border: '1px solid #ddd', display: 'inline-block' }} />
                        <code style={{ fontSize: 11 }}>{c}</code>
                      </span>
                    ))}
                  </LSpace>
                </div>
              )}
            </div>
          </div>
        )}
      </LModal>
    </div>
  );
}

// ── Characters Gallery ──────────────────────────────────

function CharactersGallery({ genome, isLoading }: { genome?: GenomeData; isLoading: boolean }) {
  const [search, setSearch] = useState('');
  const [selectedChar, setSelectedChar] = useState<any>(null);

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;

  const visuals = (genome?.modules?.character_visuals || [])
    .filter(c => !search || c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.archetype?.toLowerCase().includes(search.toLowerCase()));

  const bookChars = (genome?.characters || [])
    .filter(c => !search || c.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <LInput
        prefix={<SearchOutlined />}
        placeholder="Поиск по персонажам..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        allowClear
        style={{ marginBottom: 16, maxWidth: 400 }}
      />

      {visuals.length > 0 && (
        <>
          <h5><BgColorsOutlined style={{ marginRight: 8 }} />Визуалы персонажей</h5>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12, marginBottom: 24 }}>
            {visuals.map((char, i) => (
              <LCard
                key={char.character_id || i}
                hoverable
                size="small"
                onClick={() => setSelectedChar(char)}
                style={{ height: '100%' }}
              >
                <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <LAvatar
                    size={48}
                    style={{ backgroundColor: char.color_palette?.[0] || '#2563eb', fontSize: 20, flexShrink: 0 }}
                  >
                    {char.name?.[0]}
                  </LAvatar>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <strong style={{ fontSize: 14 }}>{char.name}</strong>
                    {char.archetype && <div><LTag color="purple" style={{ fontSize: 10, marginTop: 2 }}>{char.archetype}</LTag></div>}
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: '#666', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {char.visual_description}
                    </p>
                  </div>
                </div>

                {char.color_palette?.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', gap: 3 }}>
                    {char.color_palette.slice(0, 6).map((c: string, j: number) => (
                      <div key={j} style={{ width: 14, height: 14, borderRadius: 3, background: c, border: '1px solid #ddd' }} />
                    ))}
                  </div>
                )}
              </LCard>
            ))}
          </div>
        </>
      )}

      {bookChars.length > 0 && (
        <>
          <h5><BookOutlined style={{ marginRight: 8 }} />Персонажи книги</h5>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {bookChars.map((char, i) => (
              <LCard key={char.id || i} size="small" style={{ height: '100%' }}>
                <LSpace>
                  <LAvatar size={32} style={{ backgroundColor: '#dbeafe', color: '#2563eb' }}>{char.name?.[0]}</LAvatar>
                  <div>
                    <strong style={{ fontSize: 13 }}>{char.name}</strong>
                    {char.role && <div><span style={{ fontSize: 11, color: '#999' }}>{char.role}</span></div>}
                  </div>
                </LSpace>
              </LCard>
            ))}
          </div>
        </>
      )}

      {visuals.length === 0 && bookChars.length === 0 && <LEmpty description="Персонажи не найдены" />}

      <LModal
        title={<LSpace><EyeOutlined /> {selectedChar?.name}</LSpace>}
        open={!!selectedChar}
        onCancel={() => setSelectedChar(null)}
        footer={null}
        width={600}
      >
        {selectedChar && (
          <div>
            <div style={{ textAlign: 'center', padding: '24px 0', background: 'var(--surface-bg)', borderRadius: 8, marginBottom: 16 }}>
              <LAvatar
                size={80}
                style={{ backgroundColor: selectedChar.color_palette?.[0] || '#2563eb', fontSize: 32 }}
              >
                {selectedChar.name?.[0]}
              </LAvatar>
              <h3 style={{ margin: '12px 0 4px' }}>{selectedChar.name}</h3>
              {selectedChar.archetype && <LTag color="purple">{selectedChar.archetype}</LTag>}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div><strong>ID:</strong> <code>{selectedChar.character_id}</code></div>
              <div><strong>Архетип:</strong> {selectedChar.archetype || '—'}</div>
              <div><strong>Описание:</strong> {selectedChar.visual_description || '—'}</div>
              <div><strong>Цветовая палитра:</strong>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 4 }}>
                  {selectedChar.color_palette?.map((c: string, i: number) => (
                    <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px', background: 'var(--surface-bg)', borderRadius: 4 }}>
                      <span style={{ width: 24, height: 24, borderRadius: 4, background: c, border: '1px solid #ddd', display: 'inline-block' }} />
                      <code style={{ fontSize: 11 }}>{c}</code>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </LModal>
    </div>
  );
}

// ── Locations Gallery ──────────────────────────────────

function LocationsGallery({ genome, isLoading }: { genome?: GenomeData; isLoading: boolean }) {
  const [search, setSearch] = useState('');
  const [selectedLoc, setSelectedLoc] = useState<any>(null);

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;

  const locations = (genome?.modules?.location_visuals || [])
    .filter(l => !search || l.name.toLowerCase().includes(search.toLowerCase()));

  if (locations.length === 0) return <LEmpty description="Локации не найдены" />;

  return (
    <div>
      <LInput
        prefix={<SearchOutlined />}
        placeholder="Поиск по локациям..."
        value={search}
        onChange={e => setSearch(e.target.value)}
        allowClear
        style={{ marginBottom: 16, maxWidth: 400 }}
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
        {locations.map((loc, i) => (
          <LCard
            key={loc.location_id || i}
            hoverable
            size="small"
            onClick={() => setSelectedLoc(loc)}
            style={{ height: '100%', borderLeft: '3px solid #d97706' }}
          >
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
              <div style={{ width: 48, height: 48, borderRadius: 8, background: '#fef3c7', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <EnvironmentOutlined style={{ fontSize: 20, color: '#d97706' }} />
              </div>
              <div style={{ flex: 1 }}>
                <strong style={{ fontSize: 14 }}>{loc.name}</strong>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 1, width: '100%', marginTop: 4 }}>
                  {loc.atmosphere && <span style={{ fontSize: 12, color: '#999' }}>Атмосфера: {loc.atmosphere}</span>}
                  {loc.architecture && <span style={{ fontSize: 12, color: '#999' }}>Архитектура: {loc.architecture}</span>}
                  {loc.lighting && <span style={{ fontSize: 12, color: '#999' }}>Освещение: {loc.lighting}</span>}
                </div>
              </div>
            </div>
          </LCard>
        ))}
      </div>

      <LModal
        title={<LSpace><EyeOutlined /> {selectedLoc?.name}</LSpace>}
        open={!!selectedLoc}
        onCancel={() => setSelectedLoc(null)}
        footer={null}
        width={500}
      >
        {selectedLoc && (
          <div>
            <div style={{ textAlign: 'center', padding: '24px 0', background: '#fef3c7', borderRadius: 8, marginBottom: 16 }}>
              <EnvironmentOutlined style={{ fontSize: 48, color: '#d97706' }} />
              <h3 style={{ margin: '12px 0 0' }}>{selectedLoc.name}</h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div><strong>ID:</strong> <code>{selectedLoc.location_id}</code></div>
              <div><strong>Атмосфера:</strong> {selectedLoc.atmosphere || '—'}</div>
              <div><strong>Архитектура:</strong> {selectedLoc.architecture || '—'}</div>
              <div><strong>Освещение:</strong> {selectedLoc.lighting || '—'}</div>
            </div>
          </div>
        )}
      </LModal>
    </div>
  );
}


// ── Auto-Generate from Meaning ──────────────────────────

function AutoGenerateButton({ onDone }: { onDone: () => void }) {
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<any>(null);
  const [force, setForce] = React.useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setResult(null);
    try {
      const url = '/book/visual-genome/auto-generate' + (force ? '?force=true' : '');
      const data = await api.post<any>(url);
      setResult(data.data || data);
      if (data.data?.created > 0) onDone();
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  };

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <label style={{ fontSize: 12, color: '#999', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
        <input type="checkbox" checked={force} onChange={e => setForce(e.target.checked)} />
        Сбросить старые
      </label>
      <button
        onClick={handleGenerate}
        disabled={loading}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 12px', fontSize: 13, borderRadius: 6,
          border: '1px solid #7c3aed', background: '#7c3aed', color: '#fff',
          cursor: loading ? 'wait' : 'pointer', fontWeight: 500,
        }}
      >
        {loading ? 'Генерация...' : 'Авто-генерация из смыслов'}
      </button>
      {result && !result.error && (
        <span style={{ fontSize: 12, color: '#10b981' }}>
          Создано: {result.created}, пропущено: {result.skipped}, всего: {result.total}
        </span>
      )}
      {result?.error && (
        <span style={{ fontSize: 12, color: '#ef4444' }}>Ошибка</span>
      )}
    </div>
  );
}

// ── Main Page ──────────────────────────────────

function VisualViewContent() {
  const [showSettings, setShowSettings] = React.useState(false);
  const queryClient = useQueryClient();
  const { data: genome, isLoading } = useQuery({
    queryKey: ['genome-full'],
    queryFn: () => api.get<GenomeData>('/book/genome'),
  });

  const sceneCount = genome?.modules?.scenes?.length || 0;
  const charCount = genome?.modules?.character_visuals?.length || 0;
  const locCount = genome?.modules?.location_visuals?.length || 0;

  const items = [
    {
      key: 'scenes',
      label: <><BookOutlined /> Сцены <LTag>{sceneCount}</LTag></>,
      children: <ScenesGallery genome={genome} isLoading={isLoading} />,
    },
    {
      key: 'characters',
      label: <><TeamOutlined /> Персонажи <LTag>{charCount}</LTag></>,
      children: <CharactersGallery genome={genome} isLoading={isLoading} />,
    },
    {
      key: 'locations',
      label: <><EnvironmentOutlined /> Локации <LTag>{locCount}</LTag></>,
      children: <LocationsGallery genome={genome} isLoading={isLoading} />,
    },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>Визуал</h2>
          <span style={{ color: '#999' }}>Просмотр сцен, персонажей и локаций книги «Наследие Аркаима»</span>
        </div>
        <LSpace>
          <ComfyUIStatus />
          <AutoGenerateButton onDone={() => queryClient.invalidateQueries({ queryKey: ['genome-full'] })} />
          <LButton
            type={showSettings ? 'primary' : 'default'}
            icon={<SettingOutlined />}
            onClick={() => setShowSettings(!showSettings)}
          />
        </LSpace>
      </div>

      {showSettings && (
        <div style={{ marginBottom: 16 }}>
          <Suspense fallback={<LSpin size="small" />}><GenerationSettingsPanel compact /></Suspense>
        </div>
      )}

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        <LCard size="small" hoverable>
          <div style={{ textAlign: 'center' }}>
            <BookOutlined style={{ fontSize: 20, color: '#2563eb' }} />
            <div><strong style={{ fontSize: 18 }}>{sceneCount}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>сцен</span>
          </div>
        </LCard>
        <LCard size="small" hoverable>
          <div style={{ textAlign: 'center' }}>
            <TeamOutlined style={{ fontSize: 20, color: '#7c3aed' }} />
            <div><strong style={{ fontSize: 18 }}>{charCount}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>персонажей</span>
          </div>
        </LCard>
        <LCard size="small" hoverable>
          <div style={{ textAlign: 'center' }}>
            <EnvironmentOutlined style={{ fontSize: 20, color: '#d97706' }} />
            <div><strong style={{ fontSize: 18 }}>{locCount}</strong></div>
            <span style={{ fontSize: 11, color: '#999' }}>локаций</span>
          </div>
        </LCard>
      </div>

      <LTabs items={items} />
    </div>
  );
}

export default function VisualViewPage() {
  return (
    <ProtectedRoute>
      <VisualViewContent />
    </ProtectedRoute>
  );
}
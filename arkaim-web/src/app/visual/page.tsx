'use client';

import { useState, Suspense, lazy } from 'react';
import { LCard, LTabs, LForm, LInput, LSelect, LButton, LSpace, LInputNumber, LTable, LTag, LEmpty, LSpin, LTextArea, useLForm } from '@/shared/ui/light';
import { PictureOutlined, AudioOutlined, SendOutlined, DatabaseOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute, RoleGuard } from '@/shared/lib/guards';
import { useGenerationSettings } from '@/shared/contexts/GenerationSettingsContext';
const GenerationSettingsPanel = lazy(() => import('@/shared/ui/GenerationSettingsPanel').then(m => ({ default: m.GenerationSettingsPanel })));

type GenomeData = {
  modules?: {
    scenes?: Array<{ chapter: number; scene_id: string; title: string; characters: string[]; location: string; emotion: string; meaning_tags: string[] }>;
    character_visuals?: Array<{ character_id: string; name: string; archetype?: string; visual_description: string; color_palette: string[] }>;
    location_visuals?: Array<{ location_id: string; name: string; atmosphere?: string; architecture?: string; lighting?: string }>;
  };
};

function VisualGenPanel() {
  const { style, mood, quality } = useGenerationSettings();
  const [collapsed, setCollapsed] = useState(true);

  return (
    <LCard
      size="small"
      style={{ marginBottom: 16 }}
      title={
        <LSpace>
          <ThunderboltOutlined style={{ color: '#faad14' }} />
          <strong>Генерация</strong>
        </LSpace>
      }
      extra={
        <LButton size="small" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? 'Настройки' : 'Скрыть'}
        </LButton>
      }
    >
      {!collapsed && <Suspense fallback={<LSpin size="small" />}><GenerationSettingsPanel /></Suspense>}
      <LSpace style={{ marginTop: collapsed ? 0 : 8 }}>
        <span style={{ fontSize: 12, color: '#999' }}>
          Стиль: {style} | Настроение: {mood} | Качество: {quality}
        </span>
      </LSpace>
    </LCard>
  );
}

type SceneItem = { chapter: number; scene_id: string; title: string; characters: string[]; location: string; emotion: string; meaning_tags: string[] };

function SceneTable({ scenes }: { scenes: SceneItem[] }) {
  const { style, mood, quality, provider, size, negativePrompt } = useGenerationSettings();
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  const generateMutation = useMutation({
    mutationFn: (scene: SceneItem) => {
      const params = new URLSearchParams({
        chapter: String(scene.chapter),
        scene_id: scene.scene_id,
        style: style,
        mood: mood,
        quality: quality,
        provider: provider,
        size: size,
        negative_prompt: negativePrompt,
      });
      return api.post('/book/assets/generate?' + params.toString());
    },
    onSuccess: () => {
      alert('Изображение сгенерировано');
      setGeneratingId(null);
    },
    onError: () => {
      alert('Ошибка генерации');
      setGeneratingId(null);
    },
  });

  const sceneColumns = [
    { title: 'Глава', dataIndex: 'chapter', key: 'chapter', width: 70 },
    { title: 'ID', dataIndex: 'scene_id', key: 'scene_id', render: (v: unknown) => <code style={{ fontSize: 11 }}>{v as string}</code> },
    { title: 'Название', dataIndex: 'title', key: 'title', render: (v: unknown) => <strong>{v as string}</strong> },
    { title: 'Персонажи', dataIndex: 'characters', key: 'characters', render: (v: unknown) => (v as string[])?.map((c, i) => <LTag key={i}>{c}</LTag>) },
    { title: 'Локация', dataIndex: 'location', key: 'location' },
    { title: 'Эмоция', dataIndex: 'emotion', key: 'emotion', render: (v: unknown) => <LTag color="purple">{(v as string)}</LTag> },
    {
      title: '', key: 'action', width: 80,
      render: (_: unknown, record: unknown) => {
        const r = record as SceneItem;
        return (
        <span title="Сгенерировать изображение">
          <LButton
            size="small"
            type="link"
            icon={<ThunderboltOutlined />}
            loading={generatingId === r.scene_id}
            onClick={(e) => {
              e.stopPropagation();
              setGeneratingId(r.scene_id);
              generateMutation.mutate(r);
            }}
          />
        </span>
        );
      },
    },
  ];

  return (
    <LTable
      columns={sceneColumns}
      dataSource={scenes}
      rowKey="scene_id"
      size="small"
      pagination={{ pageSize: 10 }}
    />
  );
}

function CollectionPanel() {
  const { data: genome, isLoading } = useQuery({
    queryKey: ['genome-full'],
    queryFn: () => api.get<GenomeData>('/book/genome'),
  });
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  const { provider, size } = useGenerationSettings();

  const generateCharacterMutation = useMutation({
    mutationFn: (char: { character_id: string }) => api.post('/book/assets/generate-character?' + new URLSearchParams({
      character_id: char.character_id,
      time_of_day: 'dawn',
      generator: provider,
      size: size,
    }).toString()),
    onSuccess: () => { alert('Изображение сгенерировано'); setGeneratingId(null); },
    onError: () => { alert('Ошибка генерации'); setGeneratingId(null); },
  });

  const generateLocationMutation = useMutation({
    mutationFn: (loc: { location_id: string }) => api.post('/book/assets/generate-location?' + new URLSearchParams({
      location_id: loc.location_id,
      time_of_day: 'dawn',
      generator: provider,
      size: size,
    }).toString()),
    onSuccess: () => { alert('Изображение сгенерировано'); setGeneratingId(null); },
    onError: () => { alert('Ошибка генерации'); setGeneratingId(null); },
  });

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;

  const scenes = genome?.modules?.scenes || [];
  const characters = genome?.modules?.character_visuals || [];
  const locations = genome?.modules?.location_visuals || [];

  const characterColumns = [
    { title: 'ID', dataIndex: 'character_id', key: 'id', render: (v: unknown) => <code style={{ fontSize: 11 }}>{v as string}</code> },
    { title: 'Имя', dataIndex: 'name', key: 'name', render: (v: unknown) => <strong>{v as string}</strong> },
    { title: 'Архетип', dataIndex: 'archetype', key: 'archetype', render: (v: unknown) => v ? <LTag>{(v as string)}</LTag> : '—' },
    { title: 'Описание', dataIndex: 'visual_description', key: 'desc', render: (v: unknown) => <span style={{ maxWidth: 300, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v as string}</span> },
    { title: 'Палитра', dataIndex: 'color_palette', key: 'palette', render: (v: unknown) => (v as string[])?.slice(0, 3).map((c, i) => (
      <span key={i} style={{ display: 'inline-block', width: 16, height: 16, borderRadius: '50%', background: c, border: '1px solid #ccc', marginRight: 4 }} />
    )) },
    {
      title: '', key: 'action', width: 80,
      render: (_: unknown, record: unknown) => {
        const r = record as { character_id: string; name: string; archetype?: string; visual_description: string; color_palette: string[] };
        return (
        <span title="Сгенерировать изображение">
          <LButton
            size="small" type="link" icon={<ThunderboltOutlined />}
            loading={generatingId === r.character_id}
            onClick={(e) => {
              e.stopPropagation();
              setGeneratingId(r.character_id);
              generateCharacterMutation.mutate(r);
            }}
          />
        </span>
        );
      },
    },
  ];

  const locationColumns = [
    { title: 'ID', dataIndex: 'location_id', key: 'id', render: (v: unknown) => <code style={{ fontSize: 11 }}>{v as string}</code> },
    { title: 'Название', dataIndex: 'name', key: 'name', render: (v: unknown) => <strong>{v as string}</strong> },
    { title: 'Атмосфера', dataIndex: 'atmosphere', key: 'atmosphere' },
    { title: 'Архитектура', dataIndex: 'architecture', key: 'architecture' },
    { title: 'Освещение', dataIndex: 'lighting', key: 'lighting' },
    {
      title: '', key: 'action', width: 80,
      render: (_: unknown, record: unknown) => {
        const r = record as { location_id: string; name: string; atmosphere?: string; architecture?: string; lighting?: string };
        return (
        <span title="Сгенерировать изображение">
          <LButton
            size="small" type="link" icon={<ThunderboltOutlined />}
            loading={generatingId === r.location_id}
            onClick={(e) => {
              e.stopPropagation();
              setGeneratingId(r.location_id);
              generateLocationMutation.mutate(r);
            }}
          />
        </span>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        <LCard size="small"><strong>Сцен:</strong> {scenes.length}</LCard>
        <LCard size="small"><strong>Персонажей:</strong> {characters.length}</LCard>
        <LCard size="small"><strong>Локаций:</strong> {locations.length}</LCard>
      </div>

      <VisualGenPanel />

      <LCard title="Сцены" style={{ marginTop: 16 }}>
        {scenes.length > 0 ? (
          <SceneTable scenes={scenes} />
        ) : (
          <LEmpty description="Сцены ещё не созданы" />
        )}
      </LCard>

      <LCard title="Персонажи" style={{ marginTop: 16 }}>
        {characters.length > 0 ? (
          <LTable columns={characterColumns} dataSource={characters} rowKey="character_id" size="small" pagination={{ pageSize: 10 }} />
        ) : (
          <LEmpty description="Визуалы персонажей ещё не созданы" />
        )}
      </LCard>

      <LCard title="Локации" style={{ marginTop: 16 }}>
        {locations.length > 0 ? (
          <LTable columns={locationColumns} dataSource={locations} rowKey="location_id" size="small" pagination={{ pageSize: 10 }} />
        ) : (
          <LEmpty description="Локации ещё не созданы" />
        )}
      </LCard>
    </div>
  );
}

function SceneForm() {
  const [form, formRef] = useLForm();
  const mutation = useMutation({
    mutationFn: (values: { chapter: number; title: string; characters?: string[]; location?: string; emotion?: string; meaning_tags?: string[] }) => api.post('/book/visual-genome/scene', values),
    onSuccess: () => { alert('Сцена создана'); form.resetFields(); },
    onError: () => alert('Ошибка создания сцены'),
  });

  return (
    <LForm ref={formRef} layout="vertical" onFinish={(v: any) => mutation.mutate(v)}>
      <LForm.Item name="chapter" label="Глава" rules={[{ required: true }]}>
        <LInputNumber min={1} max={42} style={{ width: '100%' }} />
      </LForm.Item>
      <LForm.Item name="title" label="Название" rules={[{ required: true }]}>
        <LInput placeholder="Название сцены" />
      </LForm.Item>
      <LForm.Item name="characters" label="Персонажи">
        <LInput placeholder="Введите имена персонажей (через запятую)" />
      </LForm.Item>
      <LForm.Item name="location" label="Локация">
        <LInput placeholder="Место действия" />
      </LForm.Item>
      <LForm.Item name="emotion" label="Эмоция">
        <LSelect options={[
          { value: 'neutral', label: 'Neutral' },
          { value: 'warm_intimate', label: 'Warm Intimate' },
          { value: 'melancholic_dark', label: 'Melancholic Dark' },
          { value: 'hopeful_golden', label: 'Hopeful Golden' },
          { value: 'dark_mystical', label: 'Dark Mystical' },
          { value: 'dramatic_contrast', label: 'Dramatic Contrast' },
          { value: 'ethereal_light', label: 'Ethereal Light' },
          { value: 'sepia_flashback', label: 'Sepia Flashback' },
          { value: 'ceremonial_warm', label: 'Ceremonial Warm' },
          { value: 'sacred_glow', label: 'Sacred Glow' },
          { value: 'conflict', label: 'Conflict' },
          { value: 'melancholic_hopeful', label: 'Melancholic Hopeful' },
          { value: 'bright_warm', label: 'Bright Warm' },
          { value: 'calm_acceptance', label: 'Calm Acceptance' },
          { value: 'duality_contrast', label: 'Duality Contrast' },
          { value: 'conflict_civilizations', label: 'Conflict Civilizations' },
          { value: 'era_transition', label: 'Era Transition' },
          { value: 'duality_of_existence', label: 'Duality of Existence' },
          { value: 'struggle_of_opposites', label: 'Struggle of Opposites' },
          { value: 'progressive_light', label: 'Progressive Light' },
          { value: 'warm_devotion', label: 'Warm Devotion' },
          { value: 'epic_reveal', label: 'Epic Reveal' },
          { value: 'harmonious_blend', label: 'Harmonious Blend' },
          { value: 'metamorphosis', label: 'Metamorphosis' },
        ]} />
      </LForm.Item>
      <LForm.Item name="meaning_tags" label="Теги смысла">
        <LInput placeholder="Теги через запятую" />
      </LForm.Item>
      <LForm.Item>
        <LButton type="primary" htmlType="submit" loading={mutation.isPending} icon={<SendOutlined />}>
          Создать сцену
        </LButton>
      </LForm.Item>
    </LForm>
  );
}

function CharacterForm() {
  const [form, formRef] = useLForm();
  const mutation = useMutation({
    mutationFn: (values: { character_id: string; name: string; archetype?: string; visual_description?: string; color_palette?: string[] }) => api.post('/book/visual-genome/character', values),
    onSuccess: () => { alert('Визуал персонажа создан'); form.resetFields(); },
    onError: () => alert('Ошибка'),
  });

  return (
    <LForm ref={formRef} layout="vertical" onFinish={(v: any) => mutation.mutate(v)}>
      <LForm.Item name="character_id" label="ID персонажа" rules={[{ required: true }]}>
        <LInput placeholder="unique-id" />
      </LForm.Item>
      <LForm.Item name="name" label="Имя" rules={[{ required: true }]}>
        <LInput placeholder="Имя персонажа" />
      </LForm.Item>
      <LForm.Item name="archetype" label="Архетип">
        <LInput placeholder="Герой, Тень, Мудрец..." />
      </LForm.Item>
      <LForm.Item name="visual_description" label="Описание">
        <LTextArea rows={3} placeholder="Внешний вид персонажа" />
      </LForm.Item>
      <LForm.Item name="color_palette" label="Цветовая палитра">
        <LInput placeholder="#hex цвета через запятую" />
      </LForm.Item>
      <LForm.Item>
        <LButton type="primary" htmlType="submit" loading={mutation.isPending}>
          Сохранить
        </LButton>
      </LForm.Item>
    </LForm>
  );
}

function LocationForm() {
  const [form, formRef] = useLForm();
  const mutation = useMutation({
    mutationFn: (values: { location_id: string; name: string; atmosphere?: string; architecture?: string; lighting?: string }) => api.post('/book/visual-genome/location', values),
    onSuccess: () => { alert('Локация создана'); form.resetFields(); },
    onError: () => alert('Ошибка'),
  });

  return (
    <LForm ref={formRef} layout="vertical" onFinish={(v: any) => mutation.mutate(v)}>
      <LForm.Item name="location_id" label="ID локации" rules={[{ required: true }]}>
        <LInput placeholder="unique-id" />
      </LForm.Item>
      <LForm.Item name="name" label="Название" rules={[{ required: true }]}>
        <LInput placeholder="Название локации" />
      </LForm.Item>
      <LForm.Item name="atmosphere" label="Атмосфера">
        <LInput placeholder="Мрачная, светлая, таинственная..." />
      </LForm.Item>
      <LForm.Item name="architecture" label="Архитектура">
        <LInput placeholder="Описание архитектуры" />
      </LForm.Item>
      <LForm.Item name="lighting" label="Освещение">
        <LInput placeholder="Тёплое, холодное, контровое..." />
      </LForm.Item>
      <LForm.Item>
        <LButton type="primary" htmlType="submit" loading={mutation.isPending}>
          Сохранить
        </LButton>
      </LForm.Item>
    </LForm>
  );
}

function VoiceForm() {
  const [description, setDescription] = useState('');
  const mutation = useMutation({
    mutationFn: (text: string) => api.post('/book/visual-genome/from-speech', { text }),
    onSuccess: () => { alert('Описание обработано'); setDescription(''); },
    onError: () => alert('Ошибка обработки'),
  });

  return (
    <div>
      <LTextArea
        value={description}
        onChange={e => setDescription(e.target.value)}
        rows={4}
        placeholder="Опишите сцену голосом или текстом..."
      />
      <LButton
        type="primary"
        icon={<AudioOutlined />}
        style={{ marginTop: 12 }}
        loading={mutation.isPending}
        onClick={() => mutation.mutate(description)}
      >
        Обработать
      </LButton>
    </div>
  );
}

function VisualContent() {
  const items = [
    { key: 'collection', label: <><DatabaseOutlined /> Коллекция</>, children: <CollectionPanel /> },
    { key: 'scene', label: <><PictureOutlined /> Сцены</>, children: <SceneForm /> },
    { key: 'character', label: 'Персонажи', children: <CharacterForm /> },
    { key: 'location', label: 'Локации', children: <LocationForm /> },
    { key: 'voice', label: <><AudioOutlined /> Голос</>, children: <VoiceForm /> },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2><PictureOutlined /> Visual Genome</h2>
      <span style={{ display: 'block', marginBottom: 16, color: '#999' }}>
        Создавайте и управляйте визуальными описаниями сцен, персонажей и локаций
      </span>
      <LTabs items={items} />
    </div>
  );
}

export default function VisualPage() {
  return (
    <ProtectedRoute>
      <RoleGuard roles={['editor', 'admin']}>
        <VisualContent />
      </RoleGuard>
    </ProtectedRoute>
  );
}
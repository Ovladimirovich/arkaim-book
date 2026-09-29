'use client';

import { useState } from 'react';
import { LCard, LTag, LTabs, LEmpty, LSpin, LSpace, LInput, LButton, LForm, useLForm, LSelect, LInputNumber, LModal, LDivider, LAvatar, LTextArea, toast } from '@/shared/ui/light';
import { EditOutlined, PlusOutlined, DeleteOutlined, SaveOutlined, BookOutlined, TeamOutlined, EnvironmentOutlined, BulbOutlined, AudioOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute, RoleGuard } from '@/shared/lib/guards';

type GenomeData = {
  modules?: {
    scenes?: Array<{ chapter: number; scene_id: string; title: string; characters: string[]; location: string; emotion: string; meaning_tags: string[]; source?: string }>;
    character_visuals?: Array<{ character_id: string; name: string; archetype?: string; visual_description: string; color_palette: string[] }>;
    location_visuals?: Array<{ location_id: string; name: string; atmosphere?: string; architecture?: string; lighting?: string }>;
  };
  themes?: Array<{ name: string; description?: string }>;
  characters?: Array<{ id: string; name: string; role?: string; description?: string }>;
  world_entities?: Array<{ id: string; name: string; type?: string }>;
};

// ── Scenes Editor ──────────────────────────────────

function ScenesEditor({ genome, isLoading }: { genome?: GenomeData; isLoading: boolean }) {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editScene, setEditScene] = useState<{ chapter: number; scene_id: string; title: string; characters: string[]; location: string; emotion: string; meaning_tags: string[]; source?: string } | null>(null);
  const [form, formRef] = useLForm();

  const scenes = genome?.modules?.scenes || [];
  const [createLoading, setCreateLoading] = useState(false);

  const createMutation = useMutation({
    mutationFn: (values: { chapter: number; title: string; characters?: string[]; location?: string; emotion?: string; meaning_tags?: string[] }) => api.post('/book/visual-genome/scene', values),
    onSuccess: () => {
      toast.success('Сцена создана');
      setCreateOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['genome-full'] });
    },
    onError: () => toast.error('Ошибка создания'),
  });

  const handleCreate = () => {
    form.validateFields().then((values: any) => createMutation.mutate(values));
  };

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <LSpace>
          <strong>Сцен: {scenes.length}</strong>
        </LSpace>
        <LButton type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          Новая сцена
        </LButton>
      </div>

      {scenes.length === 0 ? (
        <LEmpty description="Сцены ещё не созданы" />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {scenes.map((scene, i) => (
            <LCard
              key={scene.scene_id || i}
              size="small"
              hoverable
              onClick={() => setEditScene(scene)}
              title={<LSpace><LTag color="blue">Гл. {scene.chapter}</LTag> <strong style={{ fontSize: 13 }}>{scene.title}</strong></LSpace>}
              extra={<LTag>{scene.emotion}</LTag>}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {scene.characters?.length > 0 && (
                  <div><TeamOutlined style={{ marginRight: 4, color: '#2563eb' }} />
                    <span style={{ fontSize: 12, color: '#999' }}>{scene.characters.join(', ')}</span>
                  </div>
                )}
                {scene.location && (
                  <div><EnvironmentOutlined style={{ marginRight: 4, color: '#d97706' }} />
                    <span style={{ fontSize: 12, color: '#999' }}>{scene.location}</span>
                  </div>
                )}
                {scene.meaning_tags?.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    {scene.meaning_tags.slice(0, 3).map((t: string, j: number) => (
                      <LTag key={j} style={{ fontSize: 10 }}>{t}</LTag>
                    ))}
                  </div>
                )}
              </div>
            </LCard>
          ))}
        </div>
      )}

      <LModal
        title="Новая сцена"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <LButton onClick={() => setCreateOpen(false)}>Отмена</LButton>
          <LButton type="primary" loading={createMutation.isPending} onClick={handleCreate}>Создать</LButton>
        </div>}
      >
        <LForm ref={formRef} layout="vertical">
          <LForm.Item name="chapter" label="Глава" rules={[{ required: true }]}>
            <LInputNumber min={1} max={100} style={{ width: '100%' }} />
          </LForm.Item>
          <LForm.Item name="title" label="Название" rules={[{ required: true }]}>
            <LInput placeholder="Название сцены" />
          </LForm.Item>
          <LForm.Item name="characters" label="Персонажи">
            <LInput placeholder="Введите имена через запятую" />
          </LForm.Item>
          <LForm.Item name="location" label="Локация">
            <LInput placeholder="Место действия" />
          </LForm.Item>
          <LForm.Item name="emotion" label="Эмоция">
            <LSelect options={[
              { value: 'neutral', label: 'Нейтральная' },
              { value: 'joy', label: 'Радость' },
              { value: 'sadness', label: 'Грусть' },
              { value: 'anger', label: 'Гнев' },
              { value: 'fear', label: 'Страх' },
              { value: 'surprise', label: 'Удивление' },
              { value: 'mystery', label: 'Таинственность' },
            ]} />
          </LForm.Item>
          <LForm.Item name="meaning_tags" label="Теги смысла">
            <LInput placeholder="Теги через запятую" />
          </LForm.Item>
        </LForm>
      </LModal>

      <LModal
        title={<LSpace><EditOutlined /> {editScene?.title}</LSpace>}
        open={!!editScene}
        onCancel={() => setEditScene(null)}
        footer={null}
        width={600}
      >
        {editScene && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div><strong>Глава:</strong> {editScene.chapter}</div>
            <div><strong>Сцена ID:</strong> <code>{editScene.scene_id}</code></div>
            <div><strong>Название:</strong> {editScene.title}</div>
            <div><strong>Персонажи:</strong> {editScene.characters?.map((c: string, i: number) => <LTag key={i}>{c}</LTag>) || '—'}</div>
            <div><strong>Локация:</strong> {editScene.location || '—'}</div>
            <div><strong>Эмоция:</strong> <LTag>{editScene.emotion}</LTag></div>
            <div><strong>Теги:</strong> {editScene.meaning_tags?.map((t: string, i: number) => <LTag key={i} color="purple">{t}</LTag>) || '—'}</div>
            <div><strong>Источник:</strong> {editScene.source || '—'}</div>
          </div>
        )}
      </LModal>
    </div>
  );
}

// ── Characters Editor ──────────────────────────────────

function CharactersEditor({ genome, isLoading }: { genome?: GenomeData; isLoading: boolean }) {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editChar, setEditChar] = useState<any>(null);
  const [form, formRef] = useLForm();

  const characters = genome?.modules?.character_visuals || [];
  const bookCharacters = genome?.characters || [];

  const createMutation = useMutation({
    mutationFn: (values: { character_id: string; name: string; archetype?: string; visual_description?: string; color_palette?: string[] }) => api.post('/book/visual-genome/character', values),
    onSuccess: () => {
      toast.success('Персонаж создан');
      setCreateOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['genome-full'] });
    },
    onError: () => toast.error('Ошибка создания'),
  });

  const handleCreate = () => {
    form.validateFields().then((values: any) => createMutation.mutate(values));
  };

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <LSpace>
          <strong>Визуалов: {characters.length}</strong>
          <span style={{ color: '#999' }}>· Книжных: {bookCharacters.length}</span>
        </LSpace>
        <LButton type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          Новый персонаж
        </LButton>
      </div>

      {characters.length === 0 ? (
        <LEmpty description="Визуалы персонажей ещё не созданы" />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {characters.map((char, i) => (
            <LCard
              key={char.character_id || i}
              size="small"
              hoverable
              onClick={() => setEditChar(char)}
              title={<LSpace><LAvatar size={24} style={{ backgroundColor: char.color_palette?.[0] || '#2563eb' }}>{char.name?.[0]}</LAvatar> <strong style={{ fontSize: 13 }}>{char.name}</strong></LSpace>}
              extra={char.archetype && <LTag color="purple">{char.archetype}</LTag>}
            >
              <p style={{ margin: 0, fontSize: 12, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                {char.visual_description || 'Нет описания'}
              </p>
              {char.color_palette?.length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', gap: 4 }}>
                  {char.color_palette.slice(0, 5).map((c: string, j: number) => (
                    <div key={j} style={{ width: 16, height: 16, borderRadius: 4, background: c, border: '1px solid #ddd' }} />
                  ))}
                </div>
              )}
            </LCard>
          ))}
        </div>
      )}

      <LModal
        title="Новый персонаж"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <LButton onClick={() => setCreateOpen(false)}>Отмена</LButton>
          <LButton type="primary" loading={createMutation.isPending} onClick={handleCreate}>Создать</LButton>
        </div>}
      >
        <LForm ref={formRef} layout="vertical">
          <LForm.Item name="character_id" label="ID персонажа" rules={[{ required: true }]}>
            <LInput placeholder="unique-id" />
          </LForm.Item>
          <LForm.Item name="name" label="Имя" rules={[{ required: true }]}>
            <LInput placeholder="Имя персонажа" />
          </LForm.Item>
          <LForm.Item name="archetype" label="Архетип">
            <LSelect options={[
              { value: 'Герой', label: 'Герой' },
              { value: 'Мудрец', label: 'Мудрец' },
              { value: 'Тень', label: 'Тень' },
              { value: 'Наставник', label: 'Наставник' },
              { value: 'Искатель', label: 'Искатель' },
              { value: 'Бунтарь', label: 'Бунтарь' },
            ]} />
          </LForm.Item>
          <LForm.Item name="visual_description" label="Описание">
            <LTextArea rows={3} placeholder="Внешний вид персонажа" />
          </LForm.Item>
          <LForm.Item name="color_palette" label="Цветовая палитра">
            <LInput placeholder="#hex цвета через запятую" />
          </LForm.Item>
        </LForm>
      </LModal>

      <LModal
        title={<LSpace><EditOutlined /> {editChar?.name}</LSpace>}
        open={!!editChar}
        onCancel={() => setEditChar(null)}
        footer={null}
        width={600}
      >
        {editChar && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div><strong>ID:</strong> <code>{editChar.character_id}</code></div>
            <div><strong>Имя:</strong> {editChar.name}</div>
            <div><strong>Архетип:</strong> {editChar.archetype || '—'}</div>
            <div><strong>Описание:</strong> {editChar.visual_description || '—'}</div>
            <div><strong>Палитра:</strong>
              <LSpace>
                {editChar.color_palette?.map((c: string, i: number) => (
                  <span key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 20, height: 20, borderRadius: 4, background: c, border: '1px solid #ddd', display: 'inline-block' }} />
                    <code style={{ fontSize: 11 }}>{c}</code>
                  </span>
                ))}
              </LSpace>
            </div>
          </div>
        )}
      </LModal>
    </div>
  );
}

// ── Locations Editor ──────────────────────────────────

function LocationsEditor({ genome, isLoading }: { genome?: GenomeData; isLoading: boolean }) {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editLoc, setEditLoc] = useState<any>(null);
  const [form, formRef] = useLForm();

  const locations = genome?.modules?.location_visuals || [];

  const createMutation = useMutation({
    mutationFn: (values: { location_id: string; name: string; atmosphere?: string; architecture?: string; lighting?: string }) => api.post('/book/visual-genome/location', values),
    onSuccess: () => {
      toast.success('Локация создана');
      setCreateOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['genome-full'] });
    },
    onError: () => toast.error('Ошибка создания'),
  });

  const handleCreate = () => {
    form.validateFields().then((values: any) => createMutation.mutate(values));
  };

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <strong>Локаций: {locations.length}</strong>
        <LButton type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          Новая локация
        </LButton>
      </div>

      {locations.length === 0 ? (
        <LEmpty description="Локации ещё не созданы" />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
          {locations.map((loc, i) => (
            <LCard
              key={loc.location_id || i}
              size="small"
              hoverable
              onClick={() => setEditLoc(loc)}
              title={<strong style={{ fontSize: 13 }}>{loc.name}</strong>}
              extra={<EnvironmentOutlined style={{ color: '#d97706' }} />}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {loc.atmosphere && <span style={{ fontSize: 12, color: '#999' }}>Атмосфера: {loc.atmosphere}</span>}
                {loc.architecture && <span style={{ fontSize: 12, color: '#999' }}>Архитектура: {loc.architecture}</span>}
                {loc.lighting && <span style={{ fontSize: 12, color: '#999' }}>Освещение: {loc.lighting}</span>}
              </div>
            </LCard>
          ))}
        </div>
      )}

      <LModal
        title="Новая локация"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        footer={<div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <LButton onClick={() => setCreateOpen(false)}>Отмена</LButton>
          <LButton type="primary" loading={createMutation.isPending} onClick={handleCreate}>Создать</LButton>
        </div>}
      >
        <LForm ref={formRef} layout="vertical">
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
        </LForm>
      </LModal>

      <LModal
        title={<LSpace><EditOutlined /> {editLoc?.name}</LSpace>}
        open={!!editLoc}
        onCancel={() => setEditLoc(null)}
        footer={null}
      >
        {editLoc && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div><strong>ID:</strong> <code>{editLoc.location_id}</code></div>
            <div><strong>Название:</strong> {editLoc.name}</div>
            <div><strong>Атмосфера:</strong> {editLoc.atmosphere || '—'}</div>
            <div><strong>Архитектура:</strong> {editLoc.architecture || '—'}</div>
            <div><strong>Освещение:</strong> {editLoc.lighting || '—'}</div>
          </div>
        )}
      </LModal>
    </div>
  );
}

// ── Voice Input ──────────────────────────────────

function VoiceInputSection() {
  const [text, setText] = useState('');
  const queryClient = useQueryClient();

  const processMutation = useMutation({
    mutationFn: (text: string) => api.post('/book/visual-genome/from-speech', { text }),
    onSuccess: () => {
      toast.success('Описание обработано');
      setText('');
      queryClient.invalidateQueries({ queryKey: ['genome-full'] });
    },
    onError: () => toast.error('Ошибка обработки'),
  });

  return (
    <LCard title={<><AudioOutlined /> Голосовой ввод</>}>
      <p style={{ fontSize: 13, color: '#999' }}>
        Опишите сцену текстом — AI преобразует описание в структурированные элементы.
      </p>
      <LTextArea
        value={text}
        onChange={e => setText(e.target.value)}
        rows={4}
        placeholder="Опишите сцену: «Старый воин стоит на берегу реки, закатное освещение, атмосфера меланхолии...»"
        style={{ marginBottom: 12 }}
      />
      <LButton
        type="primary"
        icon={<AudioOutlined />}
        onClick={() => processMutation.mutate(text)}
        loading={processMutation.isPending}
        disabled={!text.trim()}
      >
        Обработать
      </LButton>
    </LCard>
  );
}

// ── Main Page ──────────────────────────────────

function EditorContent() {
  const { data: genome, isLoading } = useQuery({
    queryKey: ['genome-full'],
    queryFn: () => api.get<GenomeData>('/book/genome'),
  });

  const items = [
    {
      key: 'scenes',
      label: <><BookOutlined /> Сцены</>,
      children: <ScenesEditor genome={genome} isLoading={isLoading} />,
    },
    {
      key: 'characters',
      label: <><TeamOutlined /> Персонажи</>,
      children: <CharactersEditor genome={genome} isLoading={isLoading} />,
    },
    {
      key: 'locations',
      label: <><EnvironmentOutlined /> Локации</>,
      children: <LocationsEditor genome={genome} isLoading={isLoading} />,
    },
    {
      key: 'voice',
      label: <><AudioOutlined /> Голос</>,
      children: <VoiceInputSection />,
    },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 4 }}>Редактор глав</h2>
        <span style={{ color: '#999' }}>Создавайте и редактируйте сцены, персонажей и локации книги</span>
      </div>

      <LTabs items={items} />
    </div>
  );
}

export default function EditorPage() {
  return (
    <ProtectedRoute>
      <RoleGuard roles={['editor', 'admin']}>
        <EditorContent />
      </RoleGuard>
    </ProtectedRoute>
  );
}
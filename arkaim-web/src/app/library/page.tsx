'use client';

import React, { useState } from 'react';
import { LCard, LTag, LTabs, LEmpty, LSpin, LSpace, LInput, LAvatar, LModal } from '@/shared/ui/light';
import { BookOutlined, TeamOutlined, EnvironmentOutlined, SearchOutlined, BulbOutlined, StarOutlined, EyeOutlined, HistoryOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import Link from 'next/link';

type GenomeData = {
  themes: Array<{ name: string; description?: string }>;
  characters: Array<{ id: string; name: string; role?: string; description?: string }>;
  values: Array<{ name: string; description?: string }>;
  world_entities: Array<{ id: string; name: string; type?: string }>;
  author_intent: Record<string, unknown>;
};

type LayersData = {
  knowledge_layer: string;
  meaning_layer: string;
  identity_layer: string;
  mission_layer: string;
};

type EvolutionData = {
  current_version: string;
  snapshots: Array<{ version: string; created_at: string; description?: string }>;
};

function GenomeTab({ genome, isLoading }: { genome?: GenomeData; isLoading: boolean }) {
  const [search, setSearch] = useState('');
  const [selectedItem, setSelectedItem] = useState<{ name: string; id?: string; description?: string; role?: string; type?: string } | null>(null);

  const q = search.toLowerCase();

  const themes = (genome?.themes || []).filter(item =>
    !q || (item.name || '').toLowerCase().includes(q) || (item.description || '').toLowerCase().includes(q)
  );
  const characters = (genome?.characters || []).filter(item =>
    !q || (item.name || '').toLowerCase().includes(q) || (item.role || '').toLowerCase().includes(q)
  );
  const values = (genome?.values || []).filter(item =>
    !q || (item.name || '').toLowerCase().includes(q) || (item.description || '').toLowerCase().includes(q)
  );
  const entities = (genome?.world_entities || []).filter(item =>
    !q || (item.name || '').toLowerCase().includes(q) || (item.type || '').toLowerCase().includes(q)
  );

  const input = (
    <LInput prefix={<SearchOutlined />} placeholder="Поиск по геному..." value={search} onChange={e => setSearch(e.target.value)} style={{ marginBottom: 16, maxWidth: 400 }} />
  );

  const loadingBlock = isLoading ? <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div> : null;
  const emptyBlock = (!isLoading && !genome) ? <LEmpty description="Данные генома не загружены" /> : null;
  const contentBlock = (!isLoading && genome) ? (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
      <div style={{ flex: '1 1 calc(50% - 16px)', minWidth: 300 }}>
        <LCard title={<><BulbOutlined style={{ color: '#7c3aed' }} /> Темы</>} extra={<LTag>{themes.length}</LTag>}>
          {themes.length === 0 ? <LEmpty description="Нет тем" /> : themes.map((item, i) => (
            <div key={i} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--card-border)' }}
              onClick={() => setSelectedItem(item)}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><BulbOutlined style={{ color: '#7c3aed' }} /></div>
              <div style={{ flex: 1 }}><strong>{item.name}</strong>{item.description && <div style={{ fontSize: 12, color: 'var(--foreground)' }}>{item.description}</div>}</div>
              <EyeOutlined style={{ color: 'var(--foreground)' }} />
            </div>
          ))}
        </LCard>
      </div>

      <div style={{ flex: '1 1 calc(50% - 16px)', minWidth: 300 }}>
        <LCard title={<><TeamOutlined style={{ color: '#2563eb' }} /> Персонажи</>} extra={<LTag>{characters.length}</LTag>}>
          {characters.length === 0 ? <LEmpty description="Нет персонажей" /> : characters.map((item, i) => (
            <div key={i} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--card-border)' }}
              onClick={() => setSelectedItem(item)}>
              <LAvatar size={32} style={{ backgroundColor: 'var(--card-border)', color: '#2563eb' }}>{item.name?.[0] || '?'}</LAvatar>
              <div style={{ flex: 1 }}><strong>{item.name}</strong>{item.role && <LSpace size={4}><LTag color="blue" style={{ fontSize: 10 }}>{item.role}</LTag></LSpace>}</div>
              <EyeOutlined style={{ color: 'var(--foreground)' }} />
            </div>
          ))}
        </LCard>
      </div>

      <div style={{ flex: '1 1 calc(50% - 16px)', minWidth: 300 }}>
        <LCard title={<><StarOutlined style={{ color: '#059669' }} /> Ценности</>} extra={<LTag>{values.length}</LTag>}>
          {values.length === 0 ? <LEmpty description="Нет ценностей" /> : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {values.map((item, i) => (
                <LTag key={i} color="green" style={{ padding: '4px 12px', fontSize: 13, cursor: 'pointer' }} title={item.description}
                  onClick={() => setSelectedItem(item)}>
                  {item.name}
                </LTag>
              ))}
            </div>
          )}
        </LCard>
      </div>

      <div style={{ flex: '1 1 calc(50% - 16px)', minWidth: 300 }}>
        <LCard title={<><EnvironmentOutlined style={{ color: '#d97706' }} /> Мир</>} extra={<LTag>{entities.length}</LTag>}>
          {entities.length === 0 ? <LEmpty description="Нет сущностей мира" /> : entities.map((item, i) => (
            <div key={i} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--card-border)' }}
              onClick={() => setSelectedItem(item)}>
              <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--card-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><EnvironmentOutlined style={{ color: '#d97706' }} /></div>
              <div style={{ flex: 1 }}><strong>{item.name}</strong>{item.type && <LTag style={{ fontSize: 10 }}>{item.type}</LTag>}</div>
              <EyeOutlined style={{ color: 'var(--foreground)' }} />
            </div>
          ))}
        </LCard>
      </div>
    </div>
  ) : null;

  const modal = (
    <LModal title={selectedItem?.name || ''} open={!!selectedItem} onCancel={() => setSelectedItem(null)} footer={null} width={500}>
      {selectedItem && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {selectedItem.id && <div><strong>ID:</strong> <code>{selectedItem.id}</code></div>}
          <div><strong>Название:</strong> {selectedItem.name}</div>
          {selectedItem.description && <div><strong>Описание:</strong> {selectedItem.description}</div>}
          {selectedItem.role && <div><strong>Роль:</strong> <LTag color="blue">{selectedItem.role}</LTag></div>}
          {selectedItem.type && <div><strong>Тип:</strong> <LTag>{selectedItem.type}</LTag></div>}
        </div>
      )}
    </LModal>
  );

  return (
    <div>
      {input}
      {loadingBlock}
      {emptyBlock}
      {contentBlock}
      {modal}
    </div>
  );
}

function LayersTab({ layers, isLoading }: { layers?: LayersData; isLoading: boolean }) {
  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;
  if (!layers) return <LEmpty description="Слои сознания не сформированы" />;

  const layerConfig = [
    { key: 'knowledge_layer' as const, title: 'Знание', color: '#2563eb', desc: 'Факты, события, персонажи', icon: '📚' },
    { key: 'meaning_layer' as const, title: 'Смысл', color: '#7c3aed', desc: 'Метафоры, символы, аллегории', icon: '💡' },
    { key: 'identity_layer' as const, title: 'Идентичность', color: '#059669', desc: 'Кто мы в контексте книги', icon: '🪞' },
    { key: 'mission_layer' as const, title: 'Миссия', color: '#d97706', desc: 'Зачем книга существует', icon: '🎯' },
  ];

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
      {layerConfig.map(layer => {
        const content = layers[layer.key];
        return (
          <div key={layer.key} style={{ flex: '1 1 calc(50% - 16px)', minWidth: 250 }}>
            <LCard size="small" style={{ height: '100%', borderTop: `3px solid ${layer.color}` }}
              title={<LSpace><span style={{ fontSize: 18 }}>{layer.icon}</span> <span style={{ color: layer.color }}>{layer.title}</span></LSpace>}
              extra={<span style={{ color: 'var(--foreground)', fontSize: 11 }}>{layer.desc}</span>}>
              {content ? (
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, color: 'var(--foreground)' }}>{content}</p>
              ) : (
                <span style={{ color: 'var(--foreground)', fontSize: 13, fontStyle: 'italic' }}>Слой пока не определён</span>
              )}
            </LCard>
          </div>
        );
      })}
    </div>
  );
}

function EvolutionTab({ evolution, isLoading }: { evolution?: EvolutionData; isLoading: boolean }) {
  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;
  if (!evolution) return <LEmpty description="Данные об эволюции не загружены" />;

  return (
    <div>
      <LCard size="small" style={{ marginBottom: 16 }}>
        <LSpace>
          <strong>Текущая версия:</strong>
          <LTag color="blue" style={{ fontSize: 14 }}>{evolution.current_version}</LTag>
        </LSpace>
      </LCard>

      {evolution.snapshots && evolution.snapshots.length > 0 ? (
        evolution.snapshots.map((item, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, padding: '12px 0', borderBottom: '1px solid var(--card-border)' }}>
            <HistoryOutlined style={{ fontSize: 16, color: '#2563eb', marginTop: 2 }} />
            <div>
              <LSpace><LTag>{item.version}</LTag> <span style={{ fontSize: 12, color: 'var(--foreground)' }}>{new Date(item.created_at).toLocaleString('ru')}</span></LSpace>
              {item.description && <div style={{ fontSize: 12, color: 'var(--foreground)', marginTop: 4 }}>{item.description}</div>}
            </div>
          </div>
        ))
      ) : (
        <LEmpty description="Пока нет снапшотов эволюции" />
      )}
    </div>
  );
}

function LibraryContent() {
  const { data: genome, isLoading: genomeLoading } = useQuery({
    queryKey: ['genome-full'],
    queryFn: () => api.get<GenomeData>('/book/genome'),
  });

  const { data: layers, isLoading: layersLoading } = useQuery({
    queryKey: ['book-layers'],
    queryFn: () => api.get<LayersData>('/book/layers'),
  });

  const { data: evolution, isLoading: evolutionLoading } = useQuery({
    queryKey: ['evolution-status'],
    queryFn: () => api.get<EvolutionData>('/book/evolution/status'),
  });

  const stats = genome ? {
    themes: genome.themes?.length || 0,
    characters: genome.characters?.length || 0,
    values: genome.values?.length || 0,
    entities: genome.world_entities?.length || 0,
  } : null;

  const items = [
    { key: 'genome', label: <><BookOutlined /> Геном книги</>, children: <GenomeTab genome={genome} isLoading={genomeLoading} /> },
    { key: 'layers', label: <><BulbOutlined /> Слои сознания</>, children: <LayersTab layers={layers} isLoading={layersLoading} /> },
    { key: 'evolution', label: <><HistoryOutlined /> Эволюция</>, children: <EvolutionTab evolution={evolution} isLoading={evolutionLoading} /> },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ marginBottom: 4 }}>Библиотека</h2>
          <span style={{ color: 'var(--foreground)' }}>Содержимое книги «Наследие Аркаима» — темы, персонажи, ценности, мир</span>
        </div>
        <LSpace>
          <Link href="/genres"><LTag color="purple" style={{ cursor: 'pointer', padding: '4px 12px' }}>Жанры</LTag></Link>
          <Link href="/search"><LTag color="blue" style={{ cursor: 'pointer', padding: '4px 12px' }}>Поиск</LTag></Link>
        </LSpace>
      </div>

      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <div style={{ flex: 1 }}><LCard size="small" hoverable><LSpace><BulbOutlined style={{ color: '#7c3aed', fontSize: 18 }} /><div><strong style={{ fontSize: 18 }}>{stats.themes}</strong><br /><span style={{ fontSize: 11, color: 'var(--foreground)' }}>тем</span></div></LSpace></LCard></div>
          <div style={{ flex: 1 }}><LCard size="small" hoverable><LSpace><TeamOutlined style={{ color: '#2563eb', fontSize: 18 }} /><div><strong style={{ fontSize: 18 }}>{stats.characters}</strong><br /><span style={{ fontSize: 11, color: 'var(--foreground)' }}>персонажей</span></div></LSpace></LCard></div>
          <div style={{ flex: 1 }}><LCard size="small" hoverable><LSpace><StarOutlined style={{ color: '#059669', fontSize: 18 }} /><div><strong style={{ fontSize: 18 }}>{stats.values}</strong><br /><span style={{ fontSize: 11, color: 'var(--foreground)' }}>ценностей</span></div></LSpace></LCard></div>
          <div style={{ flex: 1 }}><LCard size="small" hoverable><LSpace><EnvironmentOutlined style={{ color: '#d97706', fontSize: 18 }} /><div><strong style={{ fontSize: 18 }}>{stats.entities}</strong><br /><span style={{ fontSize: 11, color: 'var(--foreground)' }}>сущностей мира</span></div></LSpace></LCard></div>
        </div>
      )}

      <LTabs items={items} />
    </div>
  );
}

export default function LibraryPage() {
  return (
    <ProtectedRoute>
      <LibraryContent />
    </ProtectedRoute>
  );
}
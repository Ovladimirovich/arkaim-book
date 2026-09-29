'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { LCard } from '@/shared/ui/light/LCard';
import { LTag } from '@/shared/ui/light/LTag';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LEmpty } from '@/shared/ui/light/LEmpty';

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

const CARDS = [
  { key: 'characters', title: 'Персонажи', color: '#2563eb' },
  { key: 'themes', title: 'Темы', color: '#7c3aed' },
  { key: 'values', title: 'Ценности', color: '#059669' },
  { key: 'world_entities', title: 'Мир', color: '#d97706' },
  { key: 'author_intent', title: 'Замысел автора', color: '#dc2626' },
];

const LAYER_COLORS: Record<string, string> = {
  knowledge: '#2563eb',
  meaning: '#7c3aed',
  identity: '#059669',
  mission: '#d97706',
};

const LAYER_LABELS: Record<string, string> = {
  knowledge: 'Знание',
  meaning: 'Смысл',
  identity: 'Идентичность',
  mission: 'Миссия',
};

export default function AboutPage() {
  const [activeTab, setActiveTab] = useState('genome');
  const { data: genome, isLoading } = useQuery({
    queryKey: ['genome-full'],
    queryFn: () => api.get<GenomeData>('/book/genome'),
    staleTime: 600_000,
  });

  const { data: layers } = useQuery({
    queryKey: ['book-layers'],
    queryFn: () => api.get<LayersData>('/book/layers'),
    staleTime: 600_000,
  });

  const { data: evolution } = useQuery({
    queryKey: ['evolution-status'],
    queryFn: () => api.get<EvolutionData>('/book/evolution/status'),
    staleTime: 600_000,
  });

  const tabs = [
    { key: 'genome', label: 'Геном книги' },
    { key: 'layers', label: 'Слои сознания' },
    { key: 'evolution', label: 'Эволюция' },
  ];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>О книге «Наследие Аркаима»</h2>
        <p style={{ maxWidth: 720, fontSize: 16, lineHeight: 1.7, color: '#666' }}>
          Интерактивное исследование содержания книги. Изучайте персонажей, темы,
          ценности и мир, в котором происходит действие. Следите за эволюцией
          цифрового сознания книги.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--divider-color)', marginBottom: 24 }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '12px 16px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontSize: 14,
              color: activeTab === tab.key ? '#1677ff' : '#666',
              borderBottom: activeTab === tab.key ? '2px solid #1677ff' : '2px solid transparent',
              marginBottom: -1,
              fontWeight: activeTab === tab.key ? 500 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Genome Tab */}
      {activeTab === 'genome' && (
        isLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
            {CARDS.map(card => {
              const items = genome?.[card.key as keyof GenomeData];
              const isArray = Array.isArray(items);
              const count = isArray ? items.length : items ? Object.keys(items).length : 0;

              return (
                <LCard
                  key={card.key}
                  title={<span style={{ color: card.color }}>{card.title}</span>}
                  extra={<LTag>{count} шт.</LTag>}
                  style={{ height: '100%' }}
                >
                  {isArray ? (
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                      {items.slice(0, 8).map((item: { name?: string; id?: string; role?: string }, i: number) => (
                        <li key={i} style={{ padding: '4px 0', borderBottom: '1px solid #f1f5f9', fontSize: 14 }}>
                          <strong>{item.name || item.id}</strong>
                          {item.role && <span style={{ color: '#999' }}> — {item.role}</span>}
                        </li>
                      ))}
                    </ul>
                  ) : items && typeof items === 'object' ? (
                    <div style={{ fontSize: 14, color: '#666' }}>
                      {Object.entries(items).slice(0, 5).map(([k, v]) => (
                        <div key={k}><strong>{k}:</strong> {String(v)}</div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: '#999' }}>Нет данных</div>
                  )}
                </LCard>
              );
            })}
          </div>
        )
      )}

      {/* Layers Tab */}
      {activeTab === 'layers' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {layers ? (
            Object.entries(layers).map(([key, value]) => {
              const layerKey = key.replace('_layer', '');
              return (
                <LCard
                  key={key}
                  size="small"
                  title={<span style={{ color: LAYER_COLORS[layerKey] || '#333' }}>{LAYER_LABELS[layerKey] || layerKey}</span>}
                  style={{ height: '100%' }}
                >
                  <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>
                    {value || <span style={{ color: '#999' }}>Слой пока не определён</span>}
                  </p>
                </LCard>
              );
            })
          ) : (
            <LCard>
              <LEmpty description="Слои сознания ещё не сформированы. Задавайте вопросы книге — и слои начнут формироваться." />
            </LCard>
          )}
        </div>
      )}

      {/* Evolution Tab */}
      {activeTab === 'evolution' && (
        <LCard>
          {evolution ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, padding: '8px 12px', background: '#f6f8fa', borderRadius: 6 }}>
                <span style={{ fontSize: 14, color: '#666' }}>Текущая версия:</span>
                <LTag color="blue" style={{ fontSize: 14 }}>{evolution.current_version}</LTag>
              </div>
              {evolution.snapshots && evolution.snapshots.length > 0 ? (
                <div style={{ position: 'relative', paddingLeft: 20 }}>
                  <div style={{ position: 'absolute', left: 6, top: 0, bottom: 0, width: 2, background: '#f0f0f0' }} />
                  {evolution.snapshots.map((s, i) => (
                    <div key={i} style={{ position: 'relative', marginBottom: 16, paddingLeft: 16 }}>
                      <div style={{ position: 'absolute', left: -17, top: 4, width: 10, height: 10, borderRadius: '50%', background: '#52c41a', border: '2px solid #fff' }} />
                      <div style={{ fontWeight: 500 }}>{s.version}</div>
                      <div style={{ fontSize: 12, color: '#999' }}>
                        {new Date(s.created_at).toLocaleString('ru')}
                      </div>
                      {s.description && <div style={{ fontSize: 13, marginTop: 4 }}>{s.description}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <LEmpty description="Пока нет снапшотов эволюции" />
              )}
            </>
          ) : (
            <LEmpty description="Информация об эволюции недоступна" />
          )}
        </LCard>
      )}
    </div>
  );
}

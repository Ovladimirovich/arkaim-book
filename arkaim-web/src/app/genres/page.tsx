'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { LTag, LTabs, LEmpty, LSpin, LSpace, LInput, LBadge } from '@/shared/ui/light';
import { BookOutlined, SearchOutlined, BulbOutlined, HeartOutlined, StarOutlined, ThunderboltOutlined, FireOutlined, EyeOutlined, TeamOutlined, EnvironmentOutlined, CrownOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { StateView } from '@/shared/ui/StateView';

type GenomeData = {
  themes: Array<{ name: string; description?: string }>;
  characters: Array<{ id: string; name: string; role?: string; description?: string }>;
  values: Array<{ name: string; description?: string }>;
  world_entities: Array<{ id: string; name: string; type?: string }>;
  author_intent: Record<string, unknown>;
};

// Честная индикация ошибок: единое описание для StateView (как на других экранах).
function errorDescription(error: unknown): string {
  return error instanceof Error
    ? `Сервер ответил ошибкой: ${error.message}.`
    : 'Проверьте связь с сервером и повторите попытку.';
}

const GENRE_CATEGORIES = [
  { key: 'mythology', title: 'Мифология', icon: <ThunderboltOutlined />, color: '#a78bfa', keywords: ['миф', 'легенда', 'бог', 'божество', 'ритуал', 'обряд', 'древний', 'предание'] },
  { key: 'history', title: 'История', icon: <BookOutlined />, color: '#60a5fa', keywords: ['история', 'век', 'эпоха', 'царь', 'князь', 'битва', 'древний', 'цивилизация'] },
  { key: 'philosophy', title: 'Философия', icon: <EyeOutlined />, color: '#34d399', keywords: ['философия', 'смысл', 'истина', 'мудрость', 'познание', 'бытие', 'сознание'] },
  { key: 'adventure', title: 'Приключения', icon: <FireOutlined />, color: '#f87171', keywords: ['приключение', 'путешествие', 'поиск', 'открытие', 'экспедиция', 'путь'] },
  { key: 'mystery', title: 'Тайна', icon: <BulbOutlined />, color: '#818cf8', keywords: ['тайна', 'загадка', 'секрет', 'загадочный', 'неизвестный', 'пророчество'] },
  { key: 'spirituality', title: 'Духовность', icon: <StarOutlined />, color: '#fbbf24', keywords: ['духовность', 'медитация', 'осознанность', 'просветление', 'карма', 'учение'] },
];

function detectGenre(name: string, description?: string): string[] {
  const text = `${name} ${description || ''}`.toLowerCase();
  const genres: string[] = [];
  for (const cat of GENRE_CATEGORIES) {
    if (cat.keywords.some(kw => text.includes(kw))) genres.push(cat.key);
  }
  if (genres.length === 0) genres.push('other');
  return genres;
}

function ThemesByGenre({ genome, isLoading, isError, error, onRetry }: { genome?: GenomeData; isLoading: boolean; isError: boolean; error: unknown; onRetry: () => void }) {
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const router = useRouter();

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;
  // Честная индикация: при сбое — ошибка с повтором, а не ложное «Данные не загружены».
  if (isError) return <StateView state="error" title="Не удалось загрузить темы" description={errorDescription(error)} onRetry={onRetry} />;
  if (!genome) return <LEmpty description="Данные не загружены" />;

  const genreThemes: Record<string, any[]> = {};
  for (const cat of GENRE_CATEGORIES) genreThemes[cat.key] = [];
  genreThemes['other'] = [];

  for (const theme of genome.themes) {
    if (search && !theme.name.toLowerCase().includes(search.toLowerCase()) && !(theme.description || '').toLowerCase().includes(search.toLowerCase())) continue;
    for (const g of detectGenre(theme.name, theme.description)) {
      if (!genreThemes[g]) genreThemes[g] = [];
      genreThemes[g].push(theme);
    }
  }

  const filteredThemes = selectedGenre
    ? (genreThemes[selectedGenre] || [])
    : genome.themes.filter(t => !search || t.name.toLowerCase().includes(search.toLowerCase()) || (t.description || '').toLowerCase().includes(search.toLowerCase()));

  const selectedCat = GENRE_CATEGORIES.find(c => c.key === selectedGenre);

  return (
    <div>
      <LInput prefix={<SearchOutlined />} placeholder="Поиск по темам..." value={search} onChange={e => setSearch(e.target.value)} style={{ marginBottom: 16, maxWidth: 400, background: '#1e293b', borderColor: '#334155', color: '#e2e8f0' }} />

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 24 }}>
        {GENRE_CATEGORIES.map(genre => {
          const count = (genreThemes[genre.key] || []).length;
          const isActive = selectedGenre === genre.key;
          return (
            <div key={genre.key} style={{ flex: '1 1 calc(16.666% - 10px)', minWidth: 120 }}>
              <div onClick={() => setSelectedGenre(isActive ? null : genre.key)}
                style={{ padding: '14px 8px', borderRadius: 10, background: isActive ? `${genre.color}22` : '#1e293b', border: `2px solid ${isActive ? genre.color : '#334155'}`, cursor: 'pointer', textAlign: 'center', transition: 'all 0.2s' }}>
                <div style={{ color: genre.color, fontSize: 22, marginBottom: 6 }}>{genre.icon}</div>
                <span style={{ fontSize: 12, color: '#e2e8f0' }}>{genre.title}</span>
                <div style={{ marginTop: 4 }}><LBadge count={count} style={{ backgroundColor: count > 0 ? genre.color : '#475569' }} /></div>
              </div>
            </div>
          );
        })}
      </div>

      {selectedGenre && selectedCat && (
        <div style={{ marginBottom: 16, padding: '14px 18px', background: '#1e293b', border: `1px solid ${selectedCat.color}44`, borderLeft: `3px solid ${selectedCat.color}`, borderRadius: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ color: selectedCat.color }}>{selectedCat.icon}</span>
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{selectedCat.title}</span>
            <LTag style={{ background: '#334155', color: '#94a3b8', borderColor: '#475569', fontSize: 11 }}>{filteredThemes.length} тем</LTag>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {filteredThemes.map((theme, i) => (
              <div key={i} style={{ flex: '1 1 calc(33.333% - 8px)', minWidth: 200 }}>
                <div style={{ padding: '10px 12px', background: '#0f172a', borderRadius: 6, borderLeft: `2px solid ${selectedCat.color}` }}>
                  <span style={{ fontSize: 13, color: '#e2e8f0' }}>{theme.name}</span>
                  {theme.description && <div style={{ marginTop: 2 }}><span style={{ fontSize: 11, color: '#94a3b8' }}>{theme.description}</span></div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!selectedGenre && (
        <div style={{ padding: '14px 18px', background: '#1e293b', borderRadius: 10, border: '1px solid #334155' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <BookOutlined style={{ color: '#60a5fa' }} />
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>Все темы</span>
            <LTag style={{ background: '#334155', color: '#94a3b8', borderColor: '#475569', fontSize: 11 }}>{filteredThemes.length}</LTag>
          </div>
          {filteredThemes.length === 0 ? <LEmpty description="Темы не найдены" /> : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {filteredThemes.map((theme, i) => {
                const genres = detectGenre(theme.name, theme.description).filter(g => g !== 'other');
                return (
                  <div key={i} style={{ flex: '1 1 calc(33.333% - 8px)', minWidth: 200 }}>
                    <div title={theme.description} onClick={() => router.push(`/book?topic=${encodeURIComponent(theme.name)}`)}
                      style={{ padding: '10px 12px', background: '#0f172a', borderRadius: 6, border: '1px solid #1e293b', cursor: 'pointer', transition: 'border-color 0.2s' }}
                      onMouseEnter={e => (e.currentTarget.style.borderColor = '#3b82f6')}
                      onMouseLeave={e => (e.currentTarget.style.borderColor = '#1e293b')}>
                      <span style={{ fontSize: 13, color: '#e2e8f0' }}>{theme.name}</span>
                      {genres.length > 0 && (
                        <div style={{ marginTop: 4, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {genres.map(g => {
                            const cat = GENRE_CATEGORIES.find(c => c.key === g);
                            return cat ? <LTag key={g} style={{ fontSize: 10, margin: 0, background: `${cat.color}22`, color: cat.color, borderColor: `${cat.color}44` }}>{cat.title}</LTag> : null;
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ValuesTab({ genome, isLoading, isError, error, onRetry }: { genome?: GenomeData; isLoading: boolean; isError: boolean; error: unknown; onRetry: () => void }) {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'description'>('name');

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;
  // Честная индикация: при сбое — ошибка с повтором, а не ложное «Ценности не определены».
  if (isError) return <StateView state="error" title="Не удалось загрузить ценности" description={errorDescription(error)} onRetry={onRetry} />;
  if (!genome?.values || genome.values.length === 0) return <LEmpty description="Ценности не определены" />;

  const icons: Record<string, any> = { 'мудрость': <StarOutlined />, 'любовь': <HeartOutlined />, 'сила': <ThunderboltOutlined />, 'добра': <StarOutlined />, 'истина': <EyeOutlined /> };
  const colors: Record<string, string> = { 'мудрость': '#fbbf24', 'любовь': '#f87171', 'сила': '#60a5fa', 'добра': '#34d399', 'истина': '#a78bfa' };

  const filtered = genome.values
    .filter(v => !search || v.name.toLowerCase().includes(search.toLowerCase()) || (v.description || '').toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => (a[sortBy] || '').localeCompare(b[sortBy] || ''));

  return (
    <div>
      <LSpace style={{ marginBottom: 16 }} wrap>
        <LInput prefix={<SearchOutlined />} placeholder="Поиск по ценностям..." value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 300, background: '#1e293b', borderColor: '#334155', color: '#e2e8f0' }} />
        <LInput addonBefore="Сортировка" value={sortBy === 'name' ? 'По имени' : 'По описанию'} readOnly style={{ maxWidth: 200, background: '#1e293b', borderColor: '#334155', color: '#e2e8f0', cursor: 'pointer' }}
          onClick={() => setSortBy(sortBy === 'name' ? 'description' : 'name')} />
      </LSpace>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        {filtered.map((value, i) => {
          const key = Object.keys(icons).find(k => value.name.toLowerCase().includes(k)) || '';
          const color = colors[key] || '#94a3b8';
          return (
            <div key={i} style={{ flex: '1 1 calc(33.333% - 12px)', minWidth: 250 }}>
              <div style={{ padding: '16px', background: '#1e293b', border: '1px solid #334155', borderTop: `3px solid ${color}`, borderRadius: 10, height: '100%' }}>
                <div style={{ display: 'flex', alignItems: 'start', gap: 12 }}>
                  <div style={{ fontSize: 24, color, flexShrink: 0 }}>{icons[key] || <StarOutlined />}</div>
                  <div>
                    <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{value.name}</span>
                    {value.description && <div style={{ marginTop: 4 }}><span style={{ fontSize: 12, color: '#94a3b8' }}>{value.description}</span></div>}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {filtered.length === 0 && <LEmpty description="Ценности не найдены" />}
    </div>
  );
}

function WorldTab({ genome, isLoading, isError, error, onRetry }: { genome?: GenomeData; isLoading: boolean; isError: boolean; error: unknown; onRetry: () => void }) {
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const allEntities = useMemo(() => genome?.world_entities || [], [genome]);
  const characters = useMemo(() => genome?.characters || [], [genome]);

  const typeConfig: Record<string, { icon: import('react').ReactNode; color: string }> = {
    location: { icon: <EnvironmentOutlined />, color: '#60a5fa' },
    character: { icon: <TeamOutlined />, color: '#a78bfa' },
    event: { icon: <ThunderboltOutlined />, color: '#f87171' },
    concept: { icon: <BulbOutlined />, color: '#34d399' },
    object: { icon: <CrownOutlined />, color: '#fbbf24' },
  };

  const filteredCharacters = useMemo(() => characters.filter(c => !search || c.name.toLowerCase().includes(search.toLowerCase()) || (c.role || '').toLowerCase().includes(search.toLowerCase())), [characters, search]);
  const filteredEntities = useMemo(() => allEntities.filter(e => !typeFilter || e.type === typeFilter).filter(e => !search || e.name.toLowerCase().includes(search.toLowerCase())), [allEntities, typeFilter, search]);

  const byType = useMemo(() => {
    const map: Record<string, { id: string; name: string; type?: string }[]> = {};
    for (const entity of filteredEntities) {
      const t = entity.type || 'other';
      if (!map[t]) map[t] = [];
      map[t].push(entity);
    }
    return map;
  }, [filteredEntities]);

  const allTypes = useMemo(() => [...new Set(allEntities.map(e => e.type || 'other'))], [allEntities]);

  if (isLoading) return <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>;
  // Честная индикация: при сбое — ошибка с повтором, а не ложное «Данные не загружены».
  if (isError) return <StateView state="error" title="Не удалось загрузить мир книги" description={errorDescription(error)} onRetry={onRetry} />;
  if (!genome) return <LEmpty description="Данные не загружены" />;

  return (
    <div>
      <LSpace style={{ marginBottom: 16 }} wrap>
        <LInput prefix={<SearchOutlined />} placeholder="Поиск по персонажам и сущностям..." value={search} onChange={e => setSearch(e.target.value)} style={{ maxWidth: 350, background: '#1e293b', borderColor: '#334155', color: '#e2e8f0' }} />
        <LSpace size={4} wrap>
          <LTag style={{ cursor: 'pointer', background: !typeFilter ? '#3b82f6' : '#1e293b', color: !typeFilter ? '#fff' : '#94a3b8', borderColor: !typeFilter ? '#3b82f6' : '#334155' }} onClick={() => setTypeFilter(null)}>Все</LTag>
          {allTypes.map(t => {
            const config = typeConfig[t] || { icon: <BulbOutlined />, color: '#94a3b8' };
            return (
              <LTag key={t} style={{ cursor: 'pointer', background: typeFilter === t ? `${config.color}33` : '#1e293b', color: typeFilter === t ? config.color : '#94a3b8', borderColor: typeFilter === t ? config.color : '#334155' }} onClick={() => setTypeFilter(typeFilter === t ? null : t)}>
                {config.icon} {t}
              </LTag>
            );
          })}
        </LSpace>
      </LSpace>

      {filteredCharacters.length > 0 && (
        <div style={{ marginBottom: 16, padding: '14px 18px', background: '#1e293b', borderRadius: 10, border: '1px solid #334155' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <TeamOutlined style={{ color: '#a78bfa' }} />
            <span style={{ color: '#e2e8f0', fontWeight: 600 }}>Персонажи</span>
            <LTag style={{ background: '#334155', color: '#94a3b8', borderColor: '#475569', fontSize: 11 }}>{filteredCharacters.length}</LTag>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {filteredCharacters.map((char, i) => (
              <div key={char.id || i} style={{ flex: '1 1 calc(33.333% - 8px)', minWidth: 200 }}>
                <div style={{ padding: '10px 12px', background: '#0f172a', borderRadius: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 500 }}>{char.name}</span>
                    {char.role && <LTag style={{ fontSize: 10, background: '#3b82f622', color: '#60a5fa', borderColor: '#3b82f644' }}>{char.role}</LTag>}
                  </div>
                  {char.description && <div style={{ marginTop: 4 }}><span style={{ fontSize: 11, color: '#94a3b8' }}>{char.description}</span></div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(byType).length > 0 ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
          {Object.entries(byType).map(([type, entities]) => {
            const config = typeConfig[type] || { icon: <BulbOutlined />, color: '#94a3b8' };
            return (
              <div key={type} style={{ flex: '1 1 calc(33.333% - 12px)', minWidth: 250 }}>
                <div style={{ padding: '14px 18px', background: '#1e293b', borderRadius: 10, border: '1px solid #334155' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <span style={{ color: config.color }}>{config.icon}</span>
                    <LTag style={{ background: `${config.color}22`, color: config.color, borderColor: `${config.color}44` }}>{type}</LTag>
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>{entities.length}</span>
                  </div>
                  {entities.map((item: any) => (
                    <div key={item.id || item.name} style={{ padding: '4px 0', borderBottom: '1px solid #1e293b' }}>
                      <span style={{ fontSize: 13, color: '#e2e8f0' }}>{item.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <LEmpty description="Сущности не найдены" />
      )}
    </div>
  );
}

function GenresContent() {
  const { data: genome, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['genome-full'],
    queryFn: () => api.get<GenomeData>('/book/genome'),
  });

  // Честная статистика: при сбое генома — «—», а не выдуманные нули.
  const themeCount = isError ? '—' : (genome?.themes?.length || 0);
  const valueCount = isError ? '—' : (genome?.values?.length || 0);
  const entityCount = isError ? '—' : (genome?.world_entities?.length || 0) + (genome?.characters?.length || 0);

  const items = [
    { key: 'genres', label: <><BookOutlined /> Жанры</>, children: <ThemesByGenre genome={genome} isLoading={isLoading} isError={isError} error={error} onRetry={() => void refetch()} /> },
    { key: 'values', label: <><StarOutlined /> Ценности</>, children: <ValuesTab genome={genome} isLoading={isLoading} isError={isError} error={error} onRetry={() => void refetch()} /> },
    { key: 'world', label: <><EyeOutlined /> Мир</>, children: <WorldTab genome={genome} isLoading={isLoading} isError={isError} error={error} onRetry={() => void refetch()} /> },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <span style={{ fontSize: 20, fontWeight: 700, color: '#e2e8f0' }}>Жанры</span>
        <div style={{ marginTop: 4 }}><span style={{ fontSize: 14, color: '#94a3b8' }}>Темы, ценности и мир книги «Наследие Аркаима» по категориям</span></div>
      </div>

      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <div style={{ flex: 1, padding: '16px', background: '#1e293b', borderRadius: 10, border: '1px solid #334155', textAlign: 'center' }}>
          <BookOutlined style={{ fontSize: 20, color: '#60a5fa' }} />
          <div style={{ marginTop: 6 }}><span style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{themeCount}</span></div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>тем</span>
        </div>
        <div style={{ flex: 1, padding: '16px', background: '#1e293b', borderRadius: 10, border: '1px solid #334155', textAlign: 'center' }}>
          <StarOutlined style={{ fontSize: 20, color: '#fbbf24' }} />
          <div style={{ marginTop: 6 }}><span style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{valueCount}</span></div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>ценностей</span>
        </div>
        <div style={{ flex: 1, padding: '16px', background: '#1e293b', borderRadius: 10, border: '1px solid #334155', textAlign: 'center' }}>
          <EyeOutlined style={{ fontSize: 20, color: '#a78bfa' }} />
          <div style={{ marginTop: 6 }}><span style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{entityCount}</span></div>
          <span style={{ fontSize: 11, color: '#94a3b8' }}>сущностей</span>
        </div>
      </div>

      <LTabs items={items} />
    </div>
  );
}

export default function GenresPage() {
  return (
    <ProtectedRoute>
      <GenresContent />
    </ProtectedRoute>
  );
}
'use client';

import { useState } from 'react';
import { SearchOutlined, DatabaseOutlined, BookOutlined, FileTextOutlined, TeamOutlined, BulbOutlined, GlobalOutlined, CommentOutlined, LikeOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LTabs } from '@/shared/ui/light/LTabs';
import { LTable } from '@/shared/ui/light/LTable';
import { LTag } from '@/shared/ui/light/LTag';
import { LSpace } from '@/shared/ui/light/LSpace';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LInput } from '@/shared/ui/light/LInput';
import { LButton } from '@/shared/ui/light/LButton';

type SearchResult = {
  id: string;
  text: string;
  score: number;
  metadata?: Record<string, unknown>;
};

type FactResult = {
  id: string;
  statement: string;
  entity_id: string;
  confidence: number;
};

type EntityResult = {
  name: string;
  type?: string;
  resolved?: string;
};

type Interpretation = {
  id: string;
  reader_name: string;
  text: string;
  themes: string[];
  characters: string[];
  likes: number;
  created_at: string;
};

type Artifact = {
  id: string;
  reader_name: string;
  title: string;
  description: string;
  category: string;
  related_themes: string[];
  location: string;
  likes: number;
  created_at: string;
};

function SearchBar({ value, onChange, onSearch, placeholder, loading }: {
  value: string; onChange: (v: string) => void; onSearch: () => void;
  placeholder: string; loading?: boolean;
}) {
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
      <div style={{ flex: 1 }}>
        <LInput
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          onPressEnter={onSearch}
          prefix={<SearchOutlined />}
          size="large"
        />
      </div>
      <LButton onClick={onSearch} loading={loading}><SearchOutlined /> Найти</LButton>
    </div>
  );
}

function GlobalSearchPanel() {
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: knowledgeData, isLoading: knowledgeLoading } = useQuery({
    queryKey: ['search-knowledge', searchQuery],
    queryFn: () => api.post<{ results: SearchResult[] }>('/book/os/search', { query: searchQuery, n_results: 5 }),
    enabled: searchQuery.length >= 2,
  });

  const { data: communityData, isLoading: communityLoading } = useQuery({
    queryKey: ['search-community', searchQuery],
    queryFn: () => api.get<{ interpretations: Interpretation[]; artifacts: Artifact[]; total: number }>(`/book/community/search?q=${encodeURIComponent(searchQuery)}&limit=5`),
    enabled: searchQuery.length >= 2,
  });

  const isLoading = knowledgeLoading || communityLoading;
  const knowledgeResults = knowledgeData?.results || [];
  const interpretations = communityData?.interpretations || [];
  const artifacts = communityData?.artifacts || [];
  const totalResults = knowledgeResults.length + interpretations.length + artifacts.length;

  const handleSearch = () => {
    if (query.trim().length >= 2) setSearchQuery(query.trim());
  };

  return (
    <div>
      <SearchBar value={query} onChange={setQuery} onSearch={handleSearch} placeholder="Поиск по всему — знания, факты, интерпретации, артефакты..." loading={isLoading} />

      {searchQuery && !isLoading && (
        <LTag color="blue" style={{ marginBottom: 16 }}>Найдено: {totalResults} результатов</LTag>
      )}

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : totalResults > 0 ? (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {knowledgeResults.length > 0 && (
            <div style={{ flex: '1 1 400px' }}>
              <LCard title={<><BookOutlined /> Знания ({knowledgeResults.length})</>} size="small">
                {knowledgeResults.map((item: SearchResult) => (
                  <div key={item.id} style={{ padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <LSpace size={8}>
                      <LTag color={item.score > 0.7 ? 'green' : item.score > 0.4 ? 'blue' : 'default'}>
                        {(item.score * 100).toFixed(0)}%
                      </LTag>
                      <span style={{ fontSize: 13, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.text.substring(0, 80)}...
                      </span>
                    </LSpace>
                    <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{String(item.metadata?.doc_id || '')}</div>
                  </div>
                ))}
              </LCard>
            </div>
          )}

          {interpretations.length > 0 && (
            <div style={{ flex: '1 1 400px' }}>
              <LCard title={<><BulbOutlined /> Интерпретации ({interpretations.length})</>} size="small">
                {interpretations.map((item: Interpretation) => (
                  <div key={item.id} style={{ padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <LSpace size={8}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{item.reader_name}</span>
                      <LikeOutlined style={{ fontSize: 12 }} /> <span style={{ fontSize: 12 }}>{item.likes}</span>
                    </LSpace>
                    <div style={{ fontSize: 12, color: '#555', marginTop: 2 }}>{item.text.substring(0, 100)}...</div>
                    <LSpace wrap size={4} style={{ marginTop: 4 }}>
                      {item.themes.slice(0, 3).map((t, i) => <LTag key={i} style={{ fontSize: 10 }}>{t}</LTag>)}
                    </LSpace>
                  </div>
                ))}
              </LCard>
            </div>
          )}

          {artifacts.length > 0 && (
            <div style={{ flex: '1 1 400px' }}>
              <LCard title={<><DatabaseOutlined /> Артефакты ({artifacts.length})</>} size="small">
                {artifacts.map((item: Artifact) => (
                  <div key={item.id} style={{ padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <LSpace size={8}>
                      <LTag color={item.category === 'archaeology' ? 'brown' : 'blue'}>{item.category}</LTag>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{item.title}</span>
                      <LikeOutlined style={{ fontSize: 12 }} /> <span style={{ fontSize: 12 }}>{item.likes}</span>
                    </LSpace>
                    <div style={{ fontSize: 12, color: '#555', marginTop: 2 }}>{item.description.substring(0, 100)}...</div>
                    {item.location && <span style={{ fontSize: 11, color: '#999' }}> · {item.location}</span>}
                  </div>
                ))}
              </LCard>
            </div>
          )}
        </div>
      ) : searchQuery ? (
        <LEmpty description="Ничего не найдено" />
      ) : null}
    </div>
  );
}

function KnowledgeSearchPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.post<{ results: SearchResult[] }>('/book/os/search', { query: query.trim(), n_results: 20 });
      setResults(data.results || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: 'Релевантность', dataIndex: 'score', key: 'score', width: 100,
      render: (v: unknown) => {
      const score = v as number;
      return (
        <LTag color={score > 0.7 ? 'green' : score > 0.4 ? 'blue' : 'default'}>{((v as number) * 100).toFixed(0)}%</LTag>
      );
    },
    },
    {
      title: 'Текст', dataIndex: 'text', key: 'text',
      render: (v: unknown) => <span style={{ fontSize: 13 }}>{(v as string).length > 200 ? (v as string).slice(0, 200) + '...' : v as string}</span>,
    },
    {
      title: 'Документ', key: 'doc',
      render: (_: unknown, r: unknown) => <LTag>{String((r as SearchResult).metadata?.doc_id || '—')}</LTag>,
    },
  ];

  return (
    <div>
      <SearchBar value={query} onChange={setQuery} onSearch={handleSearch} placeholder="Поиск по базе знаний книги..." loading={loading} />

      {searched && (
        <LSpace style={{ marginBottom: 16 }}>
          <LTag>Найдено: {results.length} результатов</LTag>
        </LSpace>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : results.length > 0 ? (
        <LTable columns={columns} dataSource={results} rowKey="id" size="small" pagination={{ pageSize: 10 }} />
      ) : searched ? (
        <LEmpty description="Ничего не найдено" />
      ) : null}
    </div>
  );
}

function CommunitySearchPanel() {
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['community-search-tab', searchQuery],
    queryFn: () => api.get<{ interpretations: Interpretation[]; artifacts: Artifact[]; total: number }>(`/book/community/search?q=${encodeURIComponent(searchQuery)}&limit=20`),
    enabled: searchQuery.length >= 2,
  });

  const interpretations = data?.interpretations || [];
  const artifacts = data?.artifacts || [];

  const handleSearch = () => {
    if (query.trim().length >= 2) setSearchQuery(query.trim());
  };

  return (
    <div>
      <SearchBar value={query} onChange={setQuery} onSearch={handleSearch} placeholder="Поиск по интерпретациям и артефактам сообщества..." loading={isLoading} />

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : (interpretations.length + artifacts.length) > 0 ? (
        <LTabs
          items={[
            {
              key: 'interpretations',
              label: <><BulbOutlined /> Интерпретации ({interpretations.length})</>,
              children: (
                <div>
                  {interpretations.map((item: Interpretation) => (
                    <LCard key={item.id} size="small" style={{ marginBottom: 8 }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
                        <LSpace size={8}>
                          <span style={{ fontWeight: 600, fontSize: 13 }}>{item.reader_name}</span>
                          <LikeOutlined style={{ fontSize: 12 }} /> <span style={{ fontSize: 12 }}>{item.likes}</span>
                        </LSpace>
                        <span>{item.text}</span>
                        <LSpace wrap size={4}>
                          {item.themes.map((t, i) => <LTag key={i}>{t}</LTag>)}
                          {item.characters.map((c, i) => <LTag key={i} color="blue">{c}</LTag>)}
                        </LSpace>
                      </div>
                    </LCard>
                  ))}
                </div>
              ),
            },
            {
              key: 'artifacts',
              label: <><DatabaseOutlined /> Артефакты ({artifacts.length})</>,
              children: (
                <div>
                  {artifacts.map((item: Artifact) => (
                    <LCard key={item.id} size="small" style={{ marginBottom: 8 }} title={item.title}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: '100%' }}>
                        <LSpace size={8}>
                          <LTag color={item.category === 'archaeology' ? 'brown' : 'blue'}>{item.category}</LTag>
                          <span style={{ color: '#999', fontSize: 13 }}>{item.location}</span>
                          <LikeOutlined style={{ fontSize: 12 }} /> <span style={{ fontSize: 12 }}>{item.likes}</span>
                        </LSpace>
                        <span>{item.description}</span>
                        <LSpace wrap size={4}>
                          {item.related_themes.map((t, i) => <LTag key={i}>{t}</LTag>)}
                        </LSpace>
                      </div>
                    </LCard>
                  ))}
                </div>
              ),
            },
          ]}
        />
      ) : searchQuery ? (
        <LEmpty description="Ничего не найдено" />
      ) : null}
    </div>
  );
}

function FactsSearchPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<FactResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.get<{ facts: FactResult[] }>(`/book/os/facts/search?statement=${encodeURIComponent(query.trim())}`);
      setResults(data.facts || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'Утверждение', dataIndex: 'statement', key: 'statement', render: (v: unknown) => <span>{v as string}</span> },
    { title: 'Сущность', dataIndex: 'entity_id', key: 'entity', render: (v: unknown) => <LTag>{v as string}</LTag> },
    {
      title: 'Уверенность', dataIndex: 'confidence', key: 'confidence',
      render: (v: unknown) => (
        <LTag color={(v as number) > 0.7 ? 'green' : (v as number) > 0.4 ? 'blue' : 'default'}>{((v as number) * 100).toFixed(0)}%</LTag>
      ),
    },
  ];

  return (
    <div>
      <SearchBar value={query} onChange={setQuery} onSearch={handleSearch} placeholder="Поиск по фактам книги..." loading={loading} />

      {searched && (
        <LSpace style={{ marginBottom: 16 }}>
          <LTag>Найдено: {results.length} фактов</LTag>
        </LSpace>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : results.length > 0 ? (
        <LTable columns={columns} dataSource={results} rowKey="id" size="small" pagination={{ pageSize: 10 }} />
      ) : searched ? (
        <LEmpty description="Фактов не найдено" />
      ) : null}
    </div>
  );
}

function EntitiesSearchPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<EntityResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.get<{ entities: EntityResult[] }>(`/book/os/entities?query=${encodeURIComponent(query.trim())}`);
      setResults(data.entities || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'Название', dataIndex: 'name', key: 'name', render: (v: unknown) => <strong>{v as string}</strong> },
    { title: 'Тип', dataIndex: 'type', key: 'type', render: (v: unknown) => v ? <LTag>{v as string}</LTag> : '—' },
    { title: 'Разрешено', dataIndex: 'resolved', key: 'resolved', render: (v: unknown) => (v as string) || '—' },
  ];

  return (
    <div>
      <SearchBar value={query} onChange={setQuery} onSearch={handleSearch} placeholder="Поиск по сущностям (персонажи, локации, события)..." loading={loading} />

      {searched && (
        <LSpace style={{ marginBottom: 16 }}>
          <LTag>Найдено: {results.length} сущностей</LTag>
        </LSpace>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : results.length > 0 ? (
        <LTable columns={columns} dataSource={results} rowKey="name" size="small" pagination={{ pageSize: 10 }} />
      ) : searched ? (
        <LEmpty description="Сущностей не найдено" />
      ) : null}
    </div>
  );
}

function GraphSearchPanel() {
  const [entityId, setEntityId] = useState('');
  const [results, setResults] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!entityId.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.get<{ neighbors: { id: string; name: string; type: string; relationship: string }[] }>(`/book/graph/entity/${encodeURIComponent(entityId.trim())}/neighbors?depth=2`);
      setResults(data.neighbors || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', render: (v: unknown) => <LTag>{v as string}</LTag> },
    { title: 'Название', dataIndex: 'name', key: 'name', render: (v: unknown) => <strong>{v as string}</strong> },
    { title: 'Тип', dataIndex: 'type', key: 'type', render: (v: unknown) => v ? <LTag>{v as string}</LTag> : '—' },
    { title: 'Связь', dataIndex: 'relationship', key: 'rel', render: (v: unknown) => (v as string) || '—' },
  ];

  return (
    <div>
      <SearchBar value={entityId} onChange={setEntityId} onSearch={handleSearch} placeholder="Введите ID сущности для поиска связей..." loading={loading} />

      {searched && (
        <LSpace style={{ marginBottom: 16 }}>
          <LTag>Найдено: {results.length} связей</LTag>
        </LSpace>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : results.length > 0 ? (
        <LTable columns={columns} dataSource={results} rowKey="id" size="small" pagination={{ pageSize: 10 }} />
      ) : searched ? (
        <LEmpty description="Связей не найдено" />
      ) : null}
    </div>
  );
}

function SearchContent() {
  const items = [
    { key: 'global', label: <><GlobalOutlined /> Везде</>, children: <GlobalSearchPanel /> },
    { key: 'knowledge', label: <><BookOutlined /> Знания</>, children: <KnowledgeSearchPanel /> },
    { key: 'community', label: <><TeamOutlined /> Сообщество</>, children: <CommunitySearchPanel /> },
    { key: 'facts', label: <><FileTextOutlined /> Факты</>, children: <FactsSearchPanel /> },
    { key: 'entities', label: <><DatabaseOutlined /> Сущности</>, children: <EntitiesSearchPanel /> },
    { key: 'graph', label: 'Граф', children: <GraphSearchPanel /> },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <h2><SearchOutlined /> Поиск</h2>
      <p style={{ color: '#666' }}>
        Ищите информацию в базе знаний книги — знания, факты, сущности, связи, интерпретации и артефакты сообщества.
      </p>
      <LTabs items={items} defaultActiveKey="global" />
    </div>
  );
}

export default function SearchPage() {
  return (
    <ProtectedRoute>
      <SearchContent />
    </ProtectedRoute>
  );
}
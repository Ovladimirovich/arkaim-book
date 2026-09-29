'use client';

import { useState } from 'react';
import { SearchOutlined, PlusOutlined, UserOutlined, LinkOutlined, EnvironmentOutlined, CommentOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { Comments } from '@/shared/ui/Comments';
import { LCard } from '@/shared/ui/light/LCard';
import { LTag } from '@/shared/ui/light/LTag';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LStatistic } from '@/shared/ui/light/LStatistic';

const CATEGORIES = [
  { value: 'archaeology', label: 'Археология' },
  { value: 'legend', label: 'Легенда' },
  { value: 'symbol', label: 'Символ' },
  { value: 'connection', label: 'Связь' },
];

type Artifact = {
  id: string;
  reader_name: string;
  title: string;
  description: string;
  category: string;
  source: string;
  connection_to_book: string;
  related_themes: string[];
  location: string;
  url: string;
  created_at: string;
  status: string;
  likes: number;
};

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  archaeology: { label: 'Археология', color: 'brown' },
  legend: { label: 'Легенда', color: 'purple' },
  symbol: { label: 'Символ', color: 'gold' },
  connection: { label: 'Связь', color: 'blue' },
};

function ArtifactForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ title: '', description: '', category: '', source: '', connection_to_book: '', related_themes: '', location: '', url: '' });

  const submitMutation = useMutation({
    mutationFn: (values: typeof form) => api.post('/book/community/artifacts', {
      ...values,
      related_themes: values.related_themes ? values.related_themes.split(',').map((t: string) => t.trim()).filter(Boolean) : [],
    }),
    onSuccess: () => {
      alert('Артефакт отправлен на модерацию');
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      onClose();
    },
  });

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    border: '1px solid #d9d9d9',
    borderRadius: 6,
    fontSize: 14,
    outline: 'none',
    boxSizing: 'border-box',
  };

  return (
    <LCard title="Новый артефакт" size="small" style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Название *</label>
          <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Каменная стела с символами" style={inputStyle} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Описание *</label>
          <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Что вы нашли? Где? Как это выглядит?" rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Категория *</label>
          <select value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} style={inputStyle}>
            <option value="">Выберите категорию</option>
            {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Источник *</label>
          <input value={form.source} onChange={e => setForm({ ...form, source: e.target.value })} placeholder="Музей, книга, сайт, экспедиция" style={inputStyle} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Связь с книгой *</label>
          <textarea value={form.connection_to_book} onChange={e => setForm({ ...form, connection_to_book: e.target.value })} placeholder="Как это связано с 'Наследием Аркаима'?" rows={2} style={{ ...inputStyle, resize: 'vertical' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Связанные темы</label>
          <input value={form.related_themes} onChange={e => setForm({ ...form, related_themes: e.target.value })} placeholder="Аркаим, Гиперборея, энергетика мест" style={inputStyle} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Местоположение</label>
          <input value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} placeholder="Южный Урал, Россия" style={inputStyle} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Ссылка</label>
          <input value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} placeholder="https://..." style={inputStyle} />
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <LButton type="primary" onClick={() => submitMutation.mutate(form)} loading={submitMutation.isPending}>Отправить</LButton>
          <LButton onClick={onClose}>Отмена</LButton>
        </div>
      </div>
    </LCard>
  );
}

function ArtifactsContent() {
  const [showForm, setShowForm] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [sort, setSort] = useState<string>('newest');
  const [expandedComments, setExpandedComments] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['artifacts', categoryFilter, sort],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set('status', 'approved');
      params.set('sort', sort);
      if (categoryFilter) params.set('category', categoryFilter);
      return api.get<{ artifacts: Artifact[]; count: number }>(`/book/community/artifacts?${params}`);
    },
  });

  const { data: stats } = useQuery({
    queryKey: ['artifacts-stats'],
    queryFn: () => api.get<{ total: number; pending: number; categories: Record<string, number> }>('/book/community/artifacts/stats'),
  });

  const likeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/artifacts/${id}/like`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['artifacts'] }),
  });

  const artifacts = data?.artifacts || [];

  const toggleComments = (id: string) => {
    setExpandedComments(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2><SearchOutlined /> Артефакты</h2>
      <p style={{ color: '#999', marginBottom: 16 }}>Находки читателей: археология, легенды, символы, связи. Каждый артефакт — мост между книгой и реальностью.</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 16 }}>
        <LCard size="small"><LStatistic title="Всего" value={stats?.total ?? 0} /></LCard>
        <LCard size="small"><LStatistic title="Археология" value={stats?.categories?.archaeology ?? 0} valueStyle={{ color: '#8B4513' }} /></LCard>
        <LCard size="small"><LStatistic title="Легенды" value={stats?.categories?.legend ?? 0} valueStyle={{ color: '#7B1FA2' }} /></LCard>
        <LCard size="small"><LStatistic title="Связи" value={stats?.categories?.connection ?? 0} valueStyle={{ color: '#1565C0' }} /></LCard>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <LButton type="primary" icon={<PlusOutlined />} onClick={() => setShowForm(true)}>
          Добавить артефакт
        </LButton>
        <select value={categoryFilter || ''} onChange={e => setCategoryFilter(e.target.value || null)} style={{ padding: '8px 12px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 14 }}>
          <option value="">Все категории</option>
          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select value={sort} onChange={e => setSort(e.target.value)} style={{ padding: '8px 12px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 14 }}>
          <option value="newest">Сначала новые</option>
          <option value="oldest">Сначала старые</option>
          <option value="popular">По популярности</option>
        </select>
      </div>

      {showForm && <ArtifactForm onClose={() => setShowForm(false)} />}

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : artifacts.length === 0 ? (
        <LEmpty description="Пока нет артефактов. Будьте первым!" />
      ) : (
        artifacts.map((item: Artifact) => {
          const cat = CATEGORY_LABELS[item.category] || { label: item.category, color: 'default' };
          return (
            <LCard key={item.id} size="small" style={{ marginBottom: 8 }} title={item.title}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <LTag color={cat.color}>{cat.label}</LTag>
                  <UserOutlined />
                  <span style={{ color: '#999' }}>{item.reader_name}</span>
                  {item.location && <span style={{ color: '#999' }}><EnvironmentOutlined /> {item.location}</span>}
                </div>
                <p style={{ margin: 0 }}>{item.description}</p>
                <p style={{ margin: 0, fontStyle: 'italic', color: '#999' }}>Связь с книгой: {item.connection_to_book}</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {item.related_themes.map((t, i) => <LTag key={i}>{t}</LTag>)}
                </div>
                {item.url && (
                  <LButton size="small" type="link" href={item.url} target="_blank" icon={<LinkOutlined />}>
                    Источник
                  </LButton>
                )}
                <div style={{ display: 'flex', gap: 8 }}>
                  <LButton size="small" onClick={() => likeMutation.mutate(item.id)}>👍 {item.likes}</LButton>
                  <LButton size="small" icon={<CommentOutlined />} onClick={() => toggleComments(item.id)}>
                    {expandedComments.has(item.id) ? 'Скрыть' : 'Комментарии'}
                  </LButton>
                </div>
                {expandedComments.has(item.id) && (
                  <Comments parentType="artifact" parentId={item.id} />
                )}
              </div>
            </LCard>
          );
        })
      )}
    </div>
  );
}

export default function ArtifactsPage() {
  return (
    <ProtectedRoute>
      <ArtifactsContent />
    </ProtectedRoute>
  );
}

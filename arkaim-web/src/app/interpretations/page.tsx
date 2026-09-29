'use client';

import { useState } from 'react';
import { BulbOutlined, LikeOutlined, PlusOutlined, UserOutlined, CommentOutlined } from '@ant-design/icons';
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

type Interpretation = {
  id: string;
  reader_id: string;
  reader_name: string;
  text: string;
  themes: string[];
  characters: string[];
  created_at: string;
  status: string;
  likes: number;
};

function InterpretationForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ text: '', themes: '', characters: '' });

  const submitMutation = useMutation({
    mutationFn: (values: { text: string; themes?: string; characters?: string }) => api.post('/book/community/interpretations', {
      text: values.text,
      themes: values.themes ? values.themes.split(',').map((t: string) => t.trim()).filter(Boolean) : [],
      characters: values.characters ? values.characters.split(',').map((c: string) => c.trim()).filter(Boolean) : [],
    }),
    onSuccess: () => {
      alert('Интерпретация отправлена на модерацию');
      queryClient.invalidateQueries({ queryKey: ['interpretations'] });
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
  };

  return (
    <LCard title="Новая интерпретация" size="small" style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Ваша интерпретация *</label>
          <textarea
            value={form.text}
            onChange={e => setForm({ ...form, text: e.target.value })}
            placeholder="Что вы нашли в книге? Какие связи обнаружили?"
            rows={4}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Связанные темы (через запятую)</label>
          <input
            value={form.themes}
            onChange={e => setForm({ ...form, themes: e.target.value })}
            placeholder="Гиперборея, звукознание, пробуждение"
            style={inputStyle}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Связанные персонажи (через запятую)</label>
          <input
            value={form.characters}
            onChange={e => setForm({ ...form, characters: e.target.value })}
            placeholder="Велик, Учитель, Славный"
            style={inputStyle}
          />
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <LButton type="primary" onClick={() => submitMutation.mutate(form)} loading={submitMutation.isPending}>Отправить</LButton>
          <LButton onClick={onClose}>Отмена</LButton>
        </div>
      </div>
    </LCard>
  );
}

function InterpretationsContent() {
  const [showForm, setShowForm] = useState(false);
  const [sort, setSort] = useState<string>('newest');
  const [expandedComments, setExpandedComments] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['interpretations', sort],
    queryFn: () => api.get<{ interpretations: Interpretation[]; count: number }>(`/book/community/interpretations?status=approved&sort=${sort}`),
  });

  const { data: stats } = useQuery({
    queryKey: ['interpretations-stats'],
    queryFn: () => api.get<{ total: number; pending: number; approved: number }>('/book/community/interpretations/stats'),
  });

  const likeMutation = useMutation({
    mutationFn: (id: string) => api.post(`/book/community/interpretations/${id}/like`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['interpretations'] }),
  });

  const interpretations = data?.interpretations || [];

  const toggleComments = (id: string) => {
    setExpandedComments(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2><BulbOutlined /> Интерпретации</h2>
      <p style={{ color: '#999', marginBottom: 16 }}>Читатели делятся своим пониманием книги. Каждая интерпретация — новый взгляд на сокрытые знания.</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 16 }}>
        <LCard size="small"><LStatistic title="Всего" value={stats?.total ?? 0} /></LCard>
        <LCard size="small"><LStatistic title="Одобрено" value={stats?.approved ?? 0} valueStyle={{ color: '#16a34a' }} /></LCard>
        <LCard size="small"><LStatistic title="Ожидают" value={stats?.pending ?? 0} valueStyle={{ color: '#f59e0b' }} /></LCard>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <LButton type="primary" icon={<PlusOutlined />} onClick={() => setShowForm(true)}>
          Поделиться интерпретацией
        </LButton>
        <select
          value={sort}
          onChange={e => setSort(e.target.value)}
          style={{ padding: '8px 12px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 14 }}
        >
          <option value="newest">Сначала новые</option>
          <option value="oldest">Сначала старые</option>
          <option value="popular">По популярности</option>
        </select>
      </div>

      {showForm && <InterpretationForm onClose={() => setShowForm(false)} />}

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
      ) : interpretations.length === 0 ? (
        <LEmpty description="Пока нет интерпретаций. Будьте первым!" />
      ) : (
        interpretations.map((item: Interpretation) => (
          <LCard key={item.id} size="small" style={{ marginBottom: 8 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <UserOutlined />
                <strong>{item.reader_name || 'Читатель'}</strong>
                <span style={{ fontSize: 12, color: '#999' }}>{new Date(item.created_at).toLocaleString('ru')}</span>
              </div>
              <p style={{ margin: 0 }}>{item.text}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {item.themes.map((t, i) => <LTag key={i}>{t}</LTag>)}
                {item.characters.map((c, i) => <LTag key={i} color="blue">{c}</LTag>)}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <LButton size="small" icon={<LikeOutlined />} onClick={() => likeMutation.mutate(item.id)}>
                  {item.likes}
                </LButton>
                <LButton size="small" icon={<CommentOutlined />} onClick={() => toggleComments(item.id)}>
                  {expandedComments.has(item.id) ? 'Скрыть' : 'Комментарии'}
                </LButton>
              </div>
              {expandedComments.has(item.id) && (
                <Comments parentType="interpretation" parentId={item.id} />
              )}
            </div>
          </LCard>
        ))
      )}
    </div>
  );
}

export default function InterpretationsPage() {
  return (
    <ProtectedRoute>
      <InterpretationsContent />
    </ProtectedRoute>
  );
}

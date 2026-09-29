'use client';

import { useState } from 'react';
import { BulbOutlined, RiseOutlined, StarOutlined, BookOutlined, TeamOutlined, HistoryOutlined, ThunderboltOutlined, HeartOutlined, ArrowRightOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { LCard } from '@/shared/ui/light/LCard';
import { LTag } from '@/shared/ui/light/LTag';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LBadge } from '@/shared/ui/light/LBadge';

type GenomeData = {
  themes: Array<{ name: string; description?: string }>;
  characters: Array<{ id: string; name: string; role?: string; description?: string }>;
  values: Array<{ name: string; description?: string }>;
  world_entities: Array<{ id: string; name: string; type?: string }>;
};

type ReaderProfile = {
  topics: Array<{ name: string; depth: number; questions: number }>;
  questions_total: number;
  conversation_count: number;
  last_topic: string;
};

type TrendingTopic = {
  keyword: string;
  hits: number;
  sources: string[];
};

function RecommendedTopics({ genome, profile }: { genome?: GenomeData; profile?: ReaderProfile }) {
  const router = useRouter();
  if (!genome || !profile) return <LSpin />;

  const studiedNames = new Set(profile.topics?.map(t => t.name) || []);
  const studiedTopics = profile.topics || [];
  const unstudied = genome.themes.filter(t => !studiedNames.has(t.name));
  const related = genome.themes.filter(t => {
    if (studiedNames.has(t.name)) return false;
    const text = `${t.name} ${t.description || ''}`.toLowerCase();
    return studiedTopics.some(st => {
      const stWords = st.name.toLowerCase().split(' ');
      return stWords.some(w => w.length > 3 && text.includes(w));
    });
  });

  const recommendations = [...new Map([...related, ...unstudied].map(t => [t.name, t])).values()].slice(0, 8);
  if (recommendations.length === 0) return <LEmpty description="Все темы уже изучены!" />;

  return (
    <LCard title={<span><BulbOutlined /> Рекомендации для вас</span>} extra={<span style={{ fontSize: 12, color: '#999' }}>На основе вашего профиля</span>}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {recommendations.map((theme) => (
          <div
            key={theme.name}
            onClick={() => router.push('/book')}
            style={{ padding: 12, background: 'var(--card-bg)', border: '1px solid var(--card-border)', borderRadius: 8, cursor: 'pointer', transition: 'border-color 0.2s' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#2563eb')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#f0f0f0')}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 }}>
              <strong style={{ fontSize: 13 }}>{theme.name}</strong>
              <LTag color={related.includes(theme) ? 'blue' : 'green'} style={{ fontSize: 10 }}>
                {related.includes(theme) ? 'Связана' : 'Новая'}
              </LTag>
            </div>
            {theme.description && (
              <div style={{ fontSize: 11, color: '#999', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{theme.description}</div>
            )}
            <div style={{ marginTop: 8, fontSize: 12, color: '#1677ff' }}>Спросить <ArrowRightOutlined /></div>
          </div>
        ))}
      </div>
    </LCard>
  );
}

function TrendingSection() {
  const { data, isLoading } = useQuery({
    queryKey: ['trending'],
    queryFn: () => api.get<{ trending: TrendingTopic[]; total: number }>('/book/presence/trending?min_hits=1'),
  });

  if (isLoading) return <LSpin />;
  const trending = data?.trending || [];
  if (trending.length === 0) return <LEmpty description="Нет трендовых тем" />;

  return (
    <LCard title={<span><RiseOutlined /> Тренды</span>} extra={<span style={{ fontSize: 12, color: '#999' }}>Что читатели ищут</span>}>
      {trending.slice(0, 10).map((item, index) => (
        <div key={item.keyword} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--divider-color)' }}>
          <LBadge count={index + 1} style={{ backgroundColor: index < 3 ? '#2563eb' : '#d9d9d9' }}>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: index < 3 ? 'var(--surface-bg)' : 'var(--card-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <RiseOutlined style={{ color: index < 3 ? '#2563eb' : '#999' }} />
            </div>
          </LBadge>
          <div style={{ flex: 1 }}>
            <strong style={{ fontSize: 13 }}>{item.keyword}</strong>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: '#999' }}>{item.hits} упоминаний</span>
              {item.sources?.map((s, i) => <LTag key={i} style={{ fontSize: 10 }}>{s}</LTag>)}
            </div>
          </div>
        </div>
      ))}
    </LCard>
  );
}

function SuggestedQuestions({ genome, profile }: { genome?: GenomeData; profile?: ReaderProfile }) {
  const router = useRouter();
  if (!genome || !profile) return <LSpin />;

  const shallowTopics = (profile.topics || []).filter(t => t.depth < 0.5);
  const unstudied = genome.themes.filter(t => !(profile.topics || []).some(pt => pt.name === t.name));

  const suggestions = [
    ...shallowTopics.slice(0, 3).map(t => ({
      question: `Расскажи подробнее о «${t.name}»`,
      reason: `Вы изучили только ${Math.round(t.depth * 100)}%`,
      icon: <BulbOutlined style={{ color: '#d97706' }} />,
    })),
    ...unstudied.slice(0, 3).map(t => ({
      question: `Что такое «${t.name}»?`,
      reason: 'Ещё не изучено',
      icon: <StarOutlined style={{ color: '#7c3aed' }} />,
    })),
  ];

  if (suggestions.length === 0) return <LEmpty description="Все темы изучены глубоко!" />;

  return (
    <LCard title={<span><ThunderboltOutlined /> Предложенные вопросы</span>} extra={<span style={{ fontSize: 12, color: '#999' }}>Персонализированные</span>}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 8 }}>
        {suggestions.map((s, i) => (
          <div
            key={i}
            onClick={() => router.push('/book')}
            style={{ padding: '10px 14px', background: '#f8fafc', borderRadius: 8, cursor: 'pointer', border: '1px solid var(--card-border)', transition: 'border-color 0.2s', display: 'flex', gap: 10, alignItems: 'flex-start' }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#2563eb')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#e2e8f0')}
          >
            <div style={{ fontSize: 16, marginTop: 2 }}>{s.icon}</div>
            <div>
              <strong style={{ fontSize: 13 }}>{s.question}</strong>
              <div style={{ fontSize: 11, color: '#999' }}>{s.reason}</div>
            </div>
          </div>
        ))}
      </div>
    </LCard>
  );
}

function StudyProgress({ profile, genome }: { profile?: ReaderProfile; genome?: GenomeData }) {
  if (!profile || !genome) return <LSpin />;

  const totalThemes = genome.themes.length;
  const studied = profile.topics?.length || 0;
  const avgDepth = profile.topics?.length
    ? profile.topics.reduce((sum, t) => sum + t.depth, 0) / profile.topics.length
    : 0;

  const CircleProgress = ({ percent, color }: { percent: number; color: string }) => (
    <div style={{ width: 80, height: 80, position: 'relative' }}>
      <svg width="80" height="80" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="35" fill="none" stroke="#f0f0f0" strokeWidth="6" />
        <circle cx="40" cy="40" r="35" fill="none" stroke={color} strokeWidth="6" strokeDasharray={`${2 * Math.PI * 35}`} strokeDashoffset={`${2 * Math.PI * 35 * (1 - percent / 100)}`} transform="rotate(-90 40 40)" strokeLinecap="round" />
      </svg>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: 14 }}>{percent}%</div>
    </div>
  );

  return (
    <LCard title={<span><BookOutlined /> Прогресс обучения</span>}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, textAlign: 'center' }}>
        <div>
          <CircleProgress percent={totalThemes > 0 ? Math.round(studied / totalThemes * 100) : 0} color="#2563eb" />
          <div style={{ marginTop: 8 }}><strong>{studied}/{totalThemes}</strong></div>
          <div style={{ fontSize: 11, color: '#999' }}>тем изучено</div>
        </div>
        <div>
          <CircleProgress percent={Math.round(avgDepth * 100)} color={avgDepth > 0.7 ? '#52c41a' : avgDepth > 0.4 ? '#1890ff' : '#d9d9d9'} />
          <div style={{ marginTop: 8 }}><strong>{Math.round(avgDepth * 100)}%</strong></div>
          <div style={{ fontSize: 11, color: '#999' }}>средняя глубина</div>
        </div>
        <div>
          <div style={{ fontSize: 32, color: '#2563eb', marginBottom: 4 }}><BookOutlined /></div>
          <div style={{ marginTop: 8 }}><strong>{profile.questions_total}</strong></div>
          <div style={{ fontSize: 11, color: '#999' }}>вопросов задано</div>
        </div>
        <div>
          <div style={{ fontSize: 32, color: '#059669', marginBottom: 4 }}><HistoryOutlined /></div>
          <div style={{ marginTop: 8 }}><strong>{profile.conversation_count}</strong></div>
          <div style={{ fontSize: 11, color: '#999' }}>диалогов</div>
        </div>
      </div>
    </LCard>
  );
}

function RecommendationsContent() {
  const [activeTab, setActiveTab] = useState('recommendations');
  const { data: genome, isLoading: genomeLoading } = useQuery({
    queryKey: ['genome-full'],
    queryFn: () => api.get<GenomeData>('/book/genome'),
  });

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ['reader-profile'],
    queryFn: () => api.get<ReaderProfile>('/book/reader/profile'),
  });

  const isLoading = genomeLoading || profileLoading;

  const tabs = [
    { key: 'recommendations', label: 'Рекомендации', icon: <BulbOutlined /> },
    { key: 'questions', label: 'Вопросы', icon: <ThunderboltOutlined /> },
    { key: 'trending', label: 'Тренды', icon: <RiseOutlined /> },
    { key: 'progress', label: 'Прогресс', icon: <BookOutlined /> },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 600, marginBottom: 4 }}>Рекомендации</h2>
          <div style={{ color: '#999' }}>Персонализированные предложения для чтения</div>
        </div>
        <Link href="/book"><LButton type="primary" icon={<BookOutlined />}>Перейти к чату</LButton></Link>
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>
      ) : (
        <>
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
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'recommendations' && <RecommendedTopics genome={genome} profile={profile} />}
          {activeTab === 'questions' && <SuggestedQuestions genome={genome} profile={profile} />}
          {activeTab === 'trending' && <TrendingSection />}
          {activeTab === 'progress' && <StudyProgress genome={genome} profile={profile} />}
        </>
      )}
    </div>
  );
}

export default function RecommendationsPage() {
  return (
    <ProtectedRoute>
      <RecommendationsContent />
    </ProtectedRoute>
  );
}

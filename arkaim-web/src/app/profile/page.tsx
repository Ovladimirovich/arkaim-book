'use client';

function ProgressRing({ percent, size = 80 }: { percent: number; size?: number }) {
  const radius = (size - 16) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percent / 100) * circumference;
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#f0f0f0" strokeWidth={8} />
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#1890ff" strokeWidth={8} strokeDasharray={circumference} strokeDashoffset={offset} transform={`rotate(-90 ${size/2} ${size/2})`} />
      </svg>
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>{percent}%</div>
    </div>
  );
}

import { useState } from 'react';
import { UserOutlined, KeyOutlined, MailOutlined, ClockCircleOutlined, BookOutlined, HeartOutlined, TrophyOutlined, DeleteOutlined, SafetyOutlined, MessageOutlined, ReadOutlined, EditOutlined, BulbOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { useAuth } from '@/app/providers';
import { ProtectedRoute } from '@/shared/lib/guards';
import Link from 'next/link';
import { LCard } from '@/shared/ui/light/LCard';
import { LTag } from '@/shared/ui/light/LTag';
import { LInput } from '@/shared/ui/light/LInput';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpace } from '@/shared/ui/light/LSpace';
import { LStatistic } from '@/shared/ui/light/LStatistic';
import { LProgress } from '@/shared/ui/light/LProgress';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LTabs } from '@/shared/ui/light/LTabs';

type ReaderProfile = {
  reader_id: string;
  display_name: string;
  questions_total: number;
  conversation_count: number;
  last_topic: string;
  topics: Array<{ name: string; depth: number; questions: number }>;
};

type HistoryItem = { id: number; content: string; created_at: string };
type ApiKeyItem = { id: string; key_prefix: string; name?: string; last_used_at?: string; is_active: boolean; created_at: string };

type Interpretation = {
  id: string; reader_name: string; text: string; themes: string[]; status: string; likes: number; created_at: string;
};

type Artifact = {
  id: string; reader_name: string; title: string; category: string; status: string; likes: number; created_at: string;
};

function QuickActions() {
  return (
    <LCard title="Быстрые действия" size="small" style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {[
          { href: '/book', icon: <MessageOutlined />, color: '#2563eb', label: 'Задать вопрос' },
          { href: '/recommendations', icon: <TrophyOutlined />, color: '#d97706', label: 'Рекомендации' },
          { href: '/library', icon: <ReadOutlined />, color: '#059669', label: 'Библиотека' },
          { href: '/interpretations', icon: <BulbOutlined />, color: '#7c3aed', label: 'Интерпретации' },
        ].map((item, i) => (
          <Link key={i} href={item.href} style={{ flex: '1 1 120px', textDecoration: 'none' }}>
            <div style={{ textAlign: 'center', height: 80, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--card-border)', borderRadius: 8, cursor: 'pointer', transition: 'box-shadow 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'}
              onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
            >
              <div style={{ fontSize: 20, color: item.color }}>{item.icon}</div>
              <span style={{ fontSize: 12, marginTop: 4, color: '#333' }}>{item.label}</span>
            </div>
          </Link>
        ))}
      </div>
    </LCard>
  );
}

const roleColors: Record<string, string> = { admin: 'red', editor: 'blue', reader: 'green' };
const roleLabels: Record<string, string> = { admin: 'Администратор', editor: 'Редактор', reader: 'Читатель' };
const providerLabels: Record<string, string> = { telegram: 'Telegram', email: 'Email', dev: 'Разработчик' };

function UserHeader({ user, profile }: { user: { id: string; role: string; username?: string; display_name?: string; provider: string } | null; profile?: ReaderProfile }) {
  return (
    <LCard style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
        <div style={{ width: 80, height: 80, borderRadius: '50%', background: (user?.role ? roleColors[user.role] : undefined) || '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 32, color: '#fff', flexShrink: 0 }}>
          <UserOutlined />
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <h3 style={{ margin: 0 }}>{user?.display_name || user?.username || 'Пользователь'}</h3>
          <LSpace style={{ marginTop: 6 }}>
            <LTag color={user?.role ? roleColors[user.role] : 'default'}>{user?.role ? roleLabels[user.role] || user.role : '—'}</LTag>
            <LTag icon={<SafetyOutlined />}>{user?.provider ? providerLabels[user.provider] || user.provider : '—'}</LTag>
          </LSpace>
          <div style={{ marginTop: 8, color: '#999', fontSize: 13 }}>
            {profile?.questions_total ?? 0} вопросов · {profile?.conversation_count ?? 0} диалогов · {(profile?.topics?.length ?? 0)} тем
          </div>
        </div>
      </div>
    </LCard>
  );
}

function StatsCards({ profile }: { profile?: ReaderProfile }) {
  const avgDepth = profile?.topics?.length
    ? Math.round(profile.topics.reduce((sum, t) => sum + t.depth, 0) / profile.topics.length * 100) : 0;

  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
      <div style={{ flex: '1 1 120px' }}><LCard size="small"><LStatistic title="Вопросов" value={profile?.questions_total ?? 0} prefix={<BookOutlined />} valueStyle={{ fontSize: 20 }} /></LCard></div>
      <div style={{ flex: '1 1 120px' }}><LCard size="small"><LStatistic title="Диалогов" value={profile?.conversation_count ?? 0} prefix={<ClockCircleOutlined />} valueStyle={{ fontSize: 20 }} /></LCard></div>
      <div style={{ flex: '1 1 120px' }}><LCard size="small"><LStatistic title="Тем" value={profile?.topics?.length ?? 0} prefix={<HeartOutlined />} valueStyle={{ fontSize: 20 }} /></LCard></div>
      <div style={{ flex: '1 1 120px' }}><LCard size="small"><LStatistic title="Глубина" value={avgDepth} suffix="%" prefix={<TrophyOutlined />} valueStyle={{ fontSize: 20, color: avgDepth > 50 ? '#52c41a' : undefined }} /></LCard></div>
    </div>
  );
}

function AccountInfo({ user }: { user: { id: string; role: string; username?: string; display_name?: string; provider: string } | null }) {
  const rows = [
    { label: 'Имя пользователя', value: user?.username || '—' },
    { label: 'Отображаемое имя', value: user?.display_name || '—' },
    { label: 'ID', value: <code style={{ fontSize: 11 }}>{user?.id || '—'}</code> },
    { label: 'Роль', value: <LTag color={user?.role === 'admin' ? 'red' : user?.role === 'editor' ? 'blue' : 'green'}>{user?.role}</LTag> },
    { label: 'Провайдер', value: user?.provider || '—' },
  ];

  return (
    <LCard title={<><UserOutlined /> Информация об аккаунте</>}>
      <div style={{ border: '1px solid var(--divider-color)', borderRadius: 6, overflow: 'hidden' }}>
        {rows.map((r, i) => (
          <div key={i} style={{ display: 'flex', borderBottom: i < rows.length - 1 ? '1px solid var(--divider-color)' : 'none' }}>
            <div style={{ width: 160, padding: '8px 12px', background: 'var(--surface-bg)', fontSize: 13, fontWeight: 500, color: 'var(--foreground)' }}>{r.label}</div>
            <div style={{ flex: 1, padding: '8px 12px', fontSize: 13 }}>{r.value}</div>
          </div>
        ))}
      </div>
    </LCard>
  );
}

function EditProfile({ user }: { user: { id: string; role: string; username?: string; display_name?: string; provider: string } | null }) {
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const updateMutation = useMutation({
    mutationFn: (values: { display_name: string }) => api.post('/auth/update-profile', values),
    onSuccess: () => {
      setMsg('Профиль обновлён');
      queryClient.invalidateQueries({ queryKey: ['auth-user'] });
    },
    onSettled: () => setSaving(false),
  });

  const handleSave = () => {
    setSaving(true);
    setMsg(null);
    updateMutation.mutate({ display_name: displayName });
  };

  return (
    <LCard title={<><EditOutlined /> Редактировать профиль</>}>
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Отображаемое имя</label>
        <LInput value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder="Ваше имя" />
      </div>
      <LButton type="primary" onClick={handleSave} loading={saving}>Сохранить</LButton>
      {msg && <div style={{ marginTop: 8, fontSize: 13, color: '#16a34a' }}>{msg}</div>}
    </LCard>
  );
}

function MyContributions() {
  const { data: interps } = useQuery({
    queryKey: ['my-interps'],
    queryFn: () => api.get<{ interpretations: Interpretation[] }>('/book/community/interpretations/mine'),
  });

  const { data: artifacts } = useQuery({
    queryKey: ['my-artifacts'],
    queryFn: () => api.get<{ artifacts: Artifact[] }>('/book/community/artifacts/mine'),
  });

  const interpretations = interps?.interpretations || [];
  const myArtifacts = artifacts?.artifacts || [];

  const statusColors: Record<string, string> = { pending: 'orange', approved: 'green', rejected: 'red' };

  return (
    <LCard title={<><HeartOutlined /> Мои вклады в сообщество</>}>
      <LTabs
        items={[
          {
            key: 'interpretations',
            label: `Интерпретации (${interpretations.length})`,
            children: interpretations.length === 0 ? (
              <LEmpty description="Вы ещё не добавляли интерпретаций" />
            ) : (
              <div>
                {interpretations.map((item) => (
                  <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <div>
                      <span style={{ fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 300, display: 'inline-block' }}>{item.text.substring(0, 50)}...</span>
                      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                        {new Date(item.created_at).toLocaleDateString('ru')} · 👍 {item.likes}
                      </div>
                    </div>
                    <LTag color={statusColors[item.status]}>{item.status}</LTag>
                  </div>
                ))}
              </div>
            ),
          },
          {
            key: 'artifacts',
            label: `Артефакты (${myArtifacts.length})`,
            children: myArtifacts.length === 0 ? (
              <LEmpty description="Вы ещё не добавляли артефактов" />
            ) : (
              <div>
                {myArtifacts.map((item) => (
                  <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                    <div>
                      <LSpace>
                        <strong style={{ fontSize: 13 }}>{item.title}</strong>
                        <LTag>{item.category}</LTag>
                      </LSpace>
                      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>👍 {item.likes}</div>
                    </div>
                    <LTag color={statusColors[item.status]}>{item.status}</LTag>
                  </div>
                ))}
              </div>
            ),
          },
        ]}
      />
    </LCard>
  );
}

function FavoriteTopics({ topics }: { topics: Array<{ name: string; depth: number; questions: number }> }) {
  if (!topics || topics.length === 0) {
    return (
      <LCard title={<><HeartOutlined /> Изученные темы</>}>
        <LEmpty description="Начните задавать вопросы в чате" />
      </LCard>
    );
  }

  return (
    <LCard title={<><HeartOutlined /> Изученные темы</>}>
      {topics.sort((a, b) => b.depth - a.depth).slice(0, 10).map((topic, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{topic.name}</div>
            <LProgress percent={Math.round(topic.depth * 100)} size="small" strokeColor={topic.depth > 0.7 ? '#52c41a' : topic.depth > 0.4 ? '#1890ff' : '#d9d9d9'} />
          </div>
          <div style={{ textAlign: 'right', marginLeft: 12 }}>
            <div style={{ fontSize: 12, color: '#999' }}>{topic.questions} вопросов</div>
            <LTag color={topic.depth > 0.7 ? 'green' : topic.depth > 0.4 ? 'blue' : 'default'} style={{ marginTop: 2 }}>
              {Math.round(topic.depth * 100)}%
            </LTag>
          </div>
        </div>
      ))}
    </LCard>
  );
}

function RecentActivity() {
  const { data: history } = useQuery({
    queryKey: ['history-profile'],
    queryFn: () => api.get<{ data: HistoryItem[] }>('/book/reader/history?limit=10'),
  });

  const items = history?.data || [];

  return (
    <LCard title={<><ClockCircleOutlined /> Недавняя активность</>}>
      {items.length === 0 ? (
        <LEmpty description="Нет недавней активности" />
      ) : (
        <div>
          {items.map((item) => (
            <div key={item.id} style={{ padding: '6px 0', display: 'flex', gap: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#1677ff', marginTop: 5, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13 }}>{item.content}</div>
                <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{new Date(item.created_at).toLocaleString('ru')}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </LCard>
  );
}

function ApiKeysSection() {
  const queryClient = useQueryClient();
  const [newKey, setNewKey] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const { data: keys, isLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: () => api.get<ApiKeyItem[]>('/auth/api-keys'),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.post<{ key: string; key_masked: string }>('/auth/api-key'),
    onSuccess: (data) => { setNewKey(data.key); setMsg('API-ключ сгенерирован'); queryClient.invalidateQueries({ queryKey: ['api-keys'] }); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/api-keys/${id}`),
    onSuccess: () => { setMsg('Ключ удалён'); setConfirmDelete(null); queryClient.invalidateQueries({ queryKey: ['api-keys'] }); },
  });

  const activeKeys = keys?.filter(k => k.is_active) || [];

  return (
    <LCard title={<><KeyOutlined /> API-ключи</>}>
      <LButton type="primary" icon={<KeyOutlined />} onClick={() => generateMutation.mutate()} loading={generateMutation.isPending} style={{ marginBottom: 12 }}>
        Сгенерировать ключ
      </LButton>

      {msg && <div style={{ marginBottom: 8, padding: '6px 12px', background: '#f0fdf4', borderRadius: 6, fontSize: 13 }}>{msg}</div>}

      {newKey && (
        <div style={{ marginBottom: 12, padding: 12, background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0' }}>
          <strong style={{ fontSize: 12 }}>Новый ключ: </strong>
          <code style={{ fontSize: 12 }}>{newKey}</code>
          <br />
          <span style={{ fontSize: 11, color: '#d97706' }}>Сохраните ключ — он показывается только один раз!</span>
        </div>
      )}

      {isLoading ? <span style={{ color: '#999' }}>Загрузка...</span> : activeKeys.length === 0 ? (
        <span style={{ fontSize: 13, color: '#999' }}>Нет активных ключей</span>
      ) : (
        <div>
          {activeKeys.map((item) => (
            <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
              <KeyOutlined style={{ color: '#2563eb' }} />
              <div style={{ flex: 1 }}>
                <code style={{ fontSize: 12 }}>{item.key_prefix}...</code>
                <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                  {item.last_used_at ? `Последнее: ${new Date(item.last_used_at).toLocaleString('ru')}` : 'Не использован'} · {new Date(item.created_at).toLocaleDateString('ru')}
                </div>
              </div>
              {confirmDelete === item.id ? (
                <LSpace>
                  <LButton size="small" onClick={() => deleteMutation.mutate(item.id)} loading={deleteMutation.isPending}>Удалить</LButton>
                  <LButton size="small" onClick={() => setConfirmDelete(null)}>Отмена</LButton>
                </LSpace>
              ) : (
                <LButton size="small" danger icon={<DeleteOutlined />} onClick={() => setConfirmDelete(item.id)} />
              )}
            </div>
          ))}
        </div>
      )}
    </LCard>
  );
}

function EmailSubscription() {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState<string | null>(null);

  const subscribeMutation = useMutation({
    mutationFn: (val: string) => api.post('/book/email/subscribe', { email: val }),
    onSuccess: () => { setMsg('Подписка оформлена'); setEmail(''); },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes('@')) { setMsg('Введите корректный email'); return; }
    subscribeMutation.mutate(email);
  };

  return (
    <LCard title={<><MailOutlined /> Подписка на рассылку</>}>
      <p style={{ fontSize: 13, color: '#999' }}>
        Получайте уведомления о новых материалах и обновлениях книги.
      </p>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 12 }}>
          <LInput value={email} onChange={e => setEmail(e.target.value)} placeholder="your@email.com" suffix={<MailOutlined />} />
        </div>
        <LButton type="primary" htmlType="submit" loading={subscribeMutation.isPending} block>Подписаться</LButton>
      </form>
      {msg && <div style={{ marginTop: 8, fontSize: 13, color: msg.includes('Введите') ? '#ef4444' : '#16a34a' }}>{msg}</div>}
    </LCard>
  );
}

function ProfileContent() {
  const { user } = useAuth();
  const { data: profile } = useQuery({
    queryKey: ['reader-profile'],
    queryFn: () => api.get<ReaderProfile>('/book/reader/profile'),
  });

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <h2 style={{ marginBottom: 16 }}>Профиль</h2>

      <QuickActions />
      <UserHeader user={user} profile={profile} />
      <StatsCards profile={profile} />

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 55%', minWidth: 350 }}>
          <MyContributions />
          <div style={{ marginTop: 16 }}>
            <FavoriteTopics topics={profile?.topics || []} />
          </div>
          <div style={{ marginTop: 16 }}>
            <RecentActivity />
          </div>
        </div>
        <div style={{ flex: '1 1 40%', minWidth: 300 }}>
          <AccountInfo user={user} />
          <div style={{ marginTop: 16 }}><EditProfile user={user} /></div>
          <div style={{ marginTop: 16 }}><ApiKeysSection /></div>
          <div style={{ marginTop: 16 }}><EmailSubscription /></div>
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  );
}
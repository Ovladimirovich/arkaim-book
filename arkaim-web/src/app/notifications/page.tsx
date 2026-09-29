'use client';

import { useState } from 'react';
import { BellOutlined, MailOutlined, BulbOutlined, SendOutlined, CheckOutlined, CloseOutlined, ReloadOutlined, TeamOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LTabs } from '@/shared/ui/light/LTabs';
import { LTable } from '@/shared/ui/light/LTable';
import { LTag } from '@/shared/ui/light/LTag';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpace } from '@/shared/ui/light/LSpace';
import { LStatistic } from '@/shared/ui/light/LStatistic';
import { LModal } from '@/shared/ui/light/LModal';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LBadge } from '@/shared/ui/light/LBadge';

type Suggestion = {
  id: string;
  topic: string;
  reason?: string;
  suggested_action?: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at?: string;
};

type TrendingTopic = {
  keyword: string;
  hits: number;
  sources: string[];
};

type EmailDraft = {
  id: string;
  subject: string;
  status: string;
  created_at: string;
  approved_at?: string;
  sent_at?: string;
};

type EmailStats = {
  subscribers: number;
  sent: number;
  errors: number;
};

function SuggestionsPanel() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['suggestions'],
    queryFn: () => api.get('/notifications/suggestions') as Promise<{ data: Suggestion[] }>,
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/notifications/suggestions/${id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suggestions'] });
      alert('Одобрено');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.post(`/notifications/suggestions/${id}/reject`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['suggestions'] });
      alert('Отклонено');
    },
  });

  const suggestions = (data as any)?.data || [];

  const columns = [
    { title: 'Тема', dataIndex: 'topic', key: 'topic' },
    { title: 'Статус', dataIndex: 'status', key: 'status', render: (v: unknown) => <LTag color={v === 'pending' ? 'blue' : v === 'approved' ? 'green' : 'red'}>{v as string}</LTag> },
    { title: 'Действия', key: 'actions', render: (_: unknown, record: unknown) => (
      (record as Suggestion).status === 'pending' ? (
        <LSpace size={4}>
          <LButton size="small" icon={<CheckOutlined />} onClick={() => approveMutation.mutate((record as Suggestion).id)} loading={approveMutation.isPending}>Одобрить</LButton>
          <LButton size="small" icon={<CloseOutlined />} onClick={() => rejectMutation.mutate((record as Suggestion).id)} loading={rejectMutation.isPending}>Отклонить</LButton>
        </LSpace>
      ) : null
    )},
  ];

  return (
    <LTable columns={columns} dataSource={suggestions} rowKey="id" loading={isLoading} size="small" pagination={{ pageSize: 10 }} />
  );
}

function TrendingPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['trending'],
    queryFn: () => api.get('/book/trending') as Promise<{ data: TrendingTopic[] }>,
  });

  const topics = (data as any)?.data || [];

  if (isLoading) return <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>Загрузка...</div>;

  if (topics.length === 0) return <LEmpty description="Нет трендовых тем" />;

  return (
    <div>
      {topics.slice(0, 10).map((topic: TrendingTopic, i: number) => (
        <div key={topic.keyword} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f5f9' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <LBadge count={i + 1} />
            <span>{topic.keyword}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: '#666', fontSize: 12 }}>{topic.hits}</span>
            <span style={{ fontSize: 12, color: '#999' }}>{topic.sources.join(', ')}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function EmailDraftsPanel() {
  const queryClient = useQueryClient();
  const [selectedDraft, setSelectedDraft] = useState<EmailDraft | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['email-drafts'],
    queryFn: () => api.get('/notifications/email/drafts') as Promise<{ data: EmailDraft[] }>,
  });

  const { data: stats } = useQuery({
    queryKey: ['email-stats'],
    queryFn: () => api.get('/notifications/email/stats') as Promise<{ data: EmailStats }>,
  });

  const generateMutation = useMutation({
    mutationFn: () => api.post('/notifications/email/generate'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-drafts'] });
      alert('Черновик создан');
    },
  });

  const approveDraftMutation = useMutation({
    mutationFn: (id: string) => api.post(`/notifications/email/drafts/${id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-drafts'] });
      alert('Черновик одобрен');
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => api.post('/notifications/email/send'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email-drafts'] });
      queryClient.invalidateQueries({ queryKey: ['email-stats'] });
      alert('Рассылка отправлена');
    },
  });

  const drafts = (data as any)?.data || [];
  const emailStats = (stats as any)?.data;

  const columns = [
    { title: 'Тема', dataIndex: 'subject', key: 'subject' },
    { title: 'Статус', dataIndex: 'status', key: 'status', render: (v: unknown) => <LTag color={v === 'approved' ? 'green' : v === 'sent' ? 'blue' : 'orange'}>{v as string}</LTag> },
    { title: 'Создан', dataIndex: 'created_at', key: 'created_at', render: (v: unknown) => (v as string) ? new Date(v as string).toLocaleDateString('ru') : '—' },
    {
      title: 'Действия', key: 'actions', render: (_: unknown, record: unknown) => (
        <LSpace size={4}>
          <LButton size="small" onClick={() => setSelectedDraft(record as EmailDraft)}>Просмотр</LButton>
          {(record as EmailDraft).status === 'draft' && (
            <LButton size="small" icon={<CheckOutlined />} onClick={() => approveDraftMutation.mutate((record as EmailDraft).id)}>Одобрить</LButton>
          )}
        </LSpace>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        {emailStats && (
          <>
            <LCard size="small"><LStatistic title="Подписчиков" value={emailStats.subscribers} /></LCard>
            <LCard size="small"><LStatistic title="Отправлено" value={emailStats.sent} /></LCard>
            <LCard size="small"><LStatistic title="Ошибок" value={emailStats.errors} /></LCard>
          </>
        )}
      </div>
      <div style={{ marginBottom: 12 }}>
        <LSpace size={8}>
          <LButton icon={<SendOutlined />} onClick={() => generateMutation.mutate()} loading={generateMutation.isPending}>Создать черновик</LButton>
          <LButton icon={<ReloadOutlined />} onClick={() => sendMutation.mutate()} loading={sendMutation.isPending}>Отправить рассылку</LButton>
        </LSpace>
      </div>
      <LTable columns={columns} dataSource={drafts} rowKey="id" loading={isLoading} size="small" pagination={{ pageSize: 10 }} />

      <LModal
        open={!!selectedDraft}
        onCancel={() => setSelectedDraft(null)}
        title="Черновик"
      >
        {selectedDraft && (
          <div>
            <p><strong>Тема:</strong> {selectedDraft.subject}</p>
            <p><strong>Статус:</strong> {selectedDraft.status}</p>
            <p><strong>Создан:</strong> {new Date(selectedDraft.created_at).toLocaleString('ru')}</p>
            {selectedDraft.approved_at && <p><strong>Одобрен:</strong> {new Date(selectedDraft.approved_at).toLocaleString('ru')}</p>}
            {selectedDraft.sent_at && <p><strong>Отправлен:</strong> {new Date(selectedDraft.sent_at).toLocaleString('ru')}</p>}
          </div>
        )}
      </LModal>
    </div>
  );
}

function SubscribersPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ['subscribers'],
    queryFn: () => api.get('/notifications/email/subscribers') as Promise<{ data: { email: string; subscribed_at: string }[] }>,
  });

  const subscribers = (data as any)?.data || [];

  const columns = [
    { title: 'Email', dataIndex: 'email', key: 'email' },
    {
      title: 'Подписан', dataIndex: 'subscribed_at', key: 'subscribed_at',
      render: (v: unknown) => (v as string) ? new Date(v as string).toLocaleDateString('ru') : '—',
    },
  ];

  return (
    <LTable columns={columns} dataSource={subscribers} rowKey="email" loading={isLoading} size="small" pagination={{ pageSize: 20 }} />
  );
}

function NotificationsContent() {
  const items = [
    { key: 'suggestions', label: <><BulbOutlined /> Предложения</>, children: <SuggestionsPanel /> },
    { key: 'trending', label: <><BellOutlined /> Тренды</>, children: <TrendingPanel /> },
    { key: 'email', label: <><MailOutlined /> Email</>, children: <EmailDraftsPanel /> },
    { key: 'subscribers', label: <><TeamOutlined /> Подписчики</>, children: <SubscribersPanel /> },
  ];

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2><BellOutlined /> Уведомления</h2>
      <p style={{ color: '#666' }}>Предложения, тренды и email-рассылка</p>
      <LTabs items={items} />
    </div>
  );
}

export default function NotificationsPage() {
  return (
    <ProtectedRoute>
      <NotificationsContent />
    </ProtectedRoute>
  );
}
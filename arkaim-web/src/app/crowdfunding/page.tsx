'use client';

import { useState } from 'react';
import { HeartOutlined, ClockCircleOutlined, UserOutlined, TrophyOutlined, LinkOutlined, ReloadOutlined, HistoryOutlined, SettingOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LProgress } from '@/shared/ui/light/LProgress';
import { LTag } from '@/shared/ui/light/LTag';
import { LStatistic } from '@/shared/ui/light/LStatistic';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LEmpty } from '@/shared/ui/light/LEmpty';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpace } from '@/shared/ui/light/LSpace';
import { LDivider } from '@/shared/ui/light/LDivider';
import { LTabs } from '@/shared/ui/light/LTabs';
import { LTable } from '@/shared/ui/light/LTable';
import { LModal } from '@/shared/ui/light/LModal';

type Milestone = {
  id: string;
  title: string;
  target_amount: number;
  reached: boolean;
};

// Форма использует проценты для майлстоунов, конвертируем при сохранении/загрузке
type FormMilestone = number; // процент от цели

type Campaign = {
  id: string;
  title: string;
  platform: string;
  url: string;
  target_amount: number;
  current_amount: number;
  backers_count: number;
  days_left: number;
  milestones: Milestone[];
  public?: boolean;
  description?: string;
  error?: string;
  last_checked?: string;
};

type CampaignHistory = {
  campaign_id: string;
  snapshots: Array<{
    current_amount: number;
    backers_count: number;
    checked_at: string;
  }>;
  total: number;
};

function HeroSection() {
  const { data } = useQuery({
    queryKey: ['crowdfunding'],
    queryFn: () => api.get<{ campaigns: Campaign[] }>('/book/crowdfunding/status'),
  });

  const campaigns = data?.campaigns || [];
  const totalRaised = campaigns.reduce((sum, c) => sum + c.current_amount, 0);
  const totalTarget = campaigns.reduce((sum, c) => sum + c.target_amount, 0);
  const totalBackers = campaigns.reduce((sum, c) => sum + c.backers_count, 0);

  // Если кампаний нет — показываем информационную страницу подготовки
  if (campaigns.length === 0) {
    return (
      <div style={{
        background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
        borderRadius: 16, padding: '3rem 2rem', color: '#fff',
        marginBottom: 32, textAlign: 'center',
      }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>𓃉</div>
        <h1 style={{ color: '#fff', margin: '0 0 8px' }}>Поддержать развитие Arkaim</h1>
        <p style={{ color: '#94a3b8', fontSize: 16, maxWidth: 700, margin: '0 auto 24px', lineHeight: 1.6 }}>
          Arkaim — цифровое представительство книги «Наследие Аркаима». Мы развиваем базу знаний,
          раскрываем связи между темами, событиями и персонажами и создаём новые способы
          знакомства читателей с миром книги.
        </p>
        <LCard style={{ maxWidth: 600, margin: '0 auto 24px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ padding: 24, textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, color: '#fbbf24' }}>
              <span style={{ fontSize: 16 }}>⏳</span>
              <strong style={{ color: '#fff' }}>Организация сбора находится на этапе подготовки</strong>
            </div>
            <p style={{ color: '#94a3b8', fontSize: 14, margin: 0, lineHeight: 1.6 }}>
              На данный момент реальные кампании и организованный способ приёма средств отсутствуют.
              Мы готовим инфраструктуру для прозрачного финансирования развития цифрового сознания книги.
            </p>
          </div>
        </LCard>
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap', color: '#64748b', fontSize: 13 }}>
          <span>🎯 Цель сбора будет объявлена позже</span>
          <span>📋 Описание финансируемых работ — в подготовке</span>
          <span>💰 Финансовая цель и прогресс — при запуске</span>
          <span>📅 Сроки — будут установлены при старте</span>
          <span>🔗 Кнопка перехода к кампании — появится при запуске</span>
          <span>📊 Отчёт об использовании средств — после завершения этапа</span>
        </div>
      </div>
    );
  }

  // Если кампании есть — показываем обычную статистику
  return (
    <div style={{
      background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
      borderRadius: 16, padding: '3rem 2rem', color: '#fff',
      marginBottom: 32, textAlign: 'center',
    }}>
      <div style={{ fontSize: 64, marginBottom: 16 }}>𓃉</div>
      <h1 style={{ color: '#fff', margin: '0 0 8px' }}>Поддержите «Наследие Аркаима»</h1>
      <p style={{ color: '#94a3b8', fontSize: 16, maxWidth: 600, margin: '0 auto 24px' }}>
        Помогите выпустить книгу и создать цифровое сознание, которое будет жить вечно.
      </p>
      <div style={{ display: 'flex', gap: 32, justifyContent: 'center', flexWrap: 'wrap' }}>
        <LStatistic title="Цель" value={totalTarget.toLocaleString('ru')} suffix="₽" valueStyle={{ color: '#fff' }} />
        <LStatistic title="Собрано" value={totalRaised.toLocaleString('ru')} suffix="₽" valueStyle={{ color: '#3b82f6' }} />
        <LStatistic title="Бэкеров" value={totalBackers} valueStyle={{ color: '#fff' }} />
      </div>
    </div>
  );
}

function MilestoneTimeline({ milestones }: { milestones: Milestone[] }) {
  return (
    <div style={{ padding: '4px 0' }}>
      {milestones.map((m) => (
        <div key={m.id} style={{ display: 'flex', gap: 12, padding: '6px 0', position: 'relative' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: m.reached ? '#52c41a' : '#d9d9d9', flexShrink: 0 }} />
            <div style={{ width: 1, flex: 1, background: '#e8e8e8', minHeight: 16 }} />
          </div>
          <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ textDecoration: m.reached ? 'line-through' : undefined, fontSize: 13 }}>{m.title}</span>
            <LTag color={m.reached ? 'green' : 'default'}>{m.reached ? 'Достигнут' : `${m.target_amount.toLocaleString('ru')} ₽`}</LTag>
          </div>
        </div>
      ))}
    </div>
  );
}

function CampaignCard({ campaign, onHistory }: { campaign: Campaign; onHistory: (id: string) => void }) {
  const percent = campaign.target_amount > 0 ? Math.round((campaign.current_amount / campaign.target_amount) * 100) : 0;
  const isUrgent = campaign.days_left <= 7 && campaign.days_left > 0;
  const isFinished = campaign.days_left <= 0;
  const isComplete = percent >= 100;
  const reachedMilestones = campaign.milestones?.filter(m => m.reached).length || 0;
  const totalMilestones = campaign.milestones?.length || 0;

  return (
    <div style={{ border: '1px solid var(--card-border)', borderRadius: 8, padding: 16, height: '100%', background: 'var(--card-bg)', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <LSpace>
          <strong>{campaign.title}</strong>
          <LTag color={campaign.platform === 'planeta' ? 'blue' : campaign.platform === 'boom' ? 'green' : 'default'}>{campaign.platform}</LTag>
          {isUrgent && <LTag color="red">Осталось {campaign.days_left} дн.</LTag>}
          {isFinished && <LTag>Завершена</LTag>}
          {campaign.public && <LTag color="green">Публична</LTag>}
        </LSpace>
        {campaign.url && <a href={campaign.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13 }}><LinkOutlined /> Открыть</a>}
      </div>

      {campaign.description && (
        <div style={{ marginBottom: 12, padding: 12, background: 'var(--bg-secondary)', borderRadius: 6, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {campaign.description}
        </div>
      )}

      <LProgress percent={percent} status={isComplete ? 'success' : isFinished ? 'exception' : 'active'} strokeColor={isComplete ? '#52c41a' : '#1890ff'} />
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 12, color: '#999' }}>{campaign.current_amount.toLocaleString('ru')} ₽</span>
        <span style={{ fontSize: 12, color: '#999' }}>{campaign.target_amount.toLocaleString('ru')} ₽ ({percent}%)</span>
      </div>

      <div style={{ display: 'flex', gap: 16, marginTop: 16 }}>
        <LStatistic title="Собрано" value={campaign.current_amount} suffix="₽" valueStyle={{ fontSize: 16 }} />
        <LStatistic title="Бэкеров" value={campaign.backers_count} prefix={<UserOutlined />} valueStyle={{ fontSize: 16 }} />
        <LStatistic title="Осталось" value={campaign.days_left} suffix="дн." prefix={<ClockCircleOutlined />} valueStyle={{ fontSize: 16, color: isUrgent ? '#ef4444' : undefined }} />
      </div>

      {totalMilestones > 0 && (
        <>
          <LDivider style={{ margin: '12px 0' }} />
          <LSpace><TrophyOutlined /><strong>Майлстоуны</strong><LTag>{reachedMilestones}/{totalMilestones}</LTag></LSpace>
          <MilestoneTimeline milestones={campaign.milestones} />
        </>
      )}

      {campaign.error && (
        <div style={{ marginTop: 12, padding: 8, background: '#fff1f0', border: '1px solid #ffa39e', borderRadius: 6, fontSize: 12, color: '#cf1322' }}>
          <strong>Ошибка последней проверки:</strong> {campaign.error}
          {campaign.last_checked && <span style={{ marginLeft: 8 }}>({new Date(campaign.last_checked).toLocaleString('ru')})</span>}
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
        <LButton size="small" icon={<HistoryOutlined />} onClick={() => onHistory(campaign.id)}>История</LButton>
        {campaign.url && !isFinished && (
          <a href={campaign.url} target="_blank" rel="noopener noreferrer">
            <LButton size="small" icon={<HeartOutlined />}>Поддержать</LButton>
          </a>
        )}
      </div>
    </div>
  );
}

function CampaignHistoryModal({ campaignId, open, onClose }: { campaignId: string; open: boolean; onClose: () => void }) {
  const { data: history, isLoading } = useQuery({
    queryKey: ['crowdfunding-history', campaignId],
    queryFn: () => api.get<CampaignHistory>(`/book/crowdfunding/campaign/${campaignId}/history?limit=20`),
    enabled: open,
  });

  const columns = [
    { title: 'Дата', dataIndex: 'checked_at', key: 'date', render: (v: unknown) => new Date(v as string).toLocaleString('ru') },
    { title: 'Собрано', dataIndex: 'current_amount', key: 'amount', render: (v: unknown) => `${(v as number).toLocaleString('ru')} ₽` },
    { title: 'Бэкеров', dataIndex: 'backers_count', key: 'backers', render: (v: unknown) => String(v ?? '—') },
  ];

  return (
    <LModal title="История кампании" open={open} onCancel={onClose} footer={null} width={600}>
      {isLoading ? <LSpin /> : (
        <LTable columns={columns} dataSource={history?.snapshots || []} rowKey="checked_at" size="small" pagination={{ pageSize: 10 }} />
      )}
    </LModal>
  );
}

function CrowdfundingAdminPanel() {
  const queryClient = useQueryClient();
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [formEnabled, setFormEnabled] = useState(true);
  const [formInterval, setFormInterval] = useState(3600);
  const [msg, setMsg] = useState<string | null>(null);
  const [campaignModalOpen, setCampaignModalOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [campaignForm, setCampaignForm] = useState({
    id: '',
    platform: 'manual',
    url: '',
    title: '',
    target_amount: 0,
    description: '',
    public: false,
    milestones: [30, 50, 75, 100],
  });

  const { data: config } = useQuery({
    queryKey: ['crowdfunding-config'],
    queryFn: () => api.get<{ enabled: boolean; check_interval: number; campaigns: Campaign[] }>('/book/crowdfunding/config'),
  });

  const checkNowMutation = useMutation({
    mutationFn: () => api.post('/book/crowdfunding/check-now'),
    onSuccess: () => { setMsg('Проверка запущена'); queryClient.invalidateQueries({ queryKey: ['crowdfunding'] }); },
  });

  const updateConfigMutation = useMutation({
    mutationFn: (values: { enabled?: boolean; check_interval?: number }) => api.post('/book/crowdfunding/config', values),
    onSuccess: () => { setMsg('Конфигурация обновлена'); queryClient.invalidateQueries({ queryKey: ['crowdfunding-config'] }); setConfigModalOpen(false); },
  });

  const updateCampaignsMutation = useMutation({
    mutationFn: (campaigns: Campaign[]) => api.post('/book/crowdfunding/config', campaigns),
    onSuccess: () => { setMsg('Кампании обновлены'); queryClient.invalidateQueries({ queryKey: ['crowdfunding-config'] }); queryClient.invalidateQueries({ queryKey: ['crowdfunding'] }); setCampaignModalOpen(false); },
  });

  const handleSaveConfig = () => {
    updateConfigMutation.mutate({ enabled: formEnabled, check_interval: formInterval });
  };

  const showConfig = () => {
    setFormEnabled(config?.enabled ?? true);
    setFormInterval(config?.check_interval ?? 3600);
    setConfigModalOpen(true);
  };

  const openCampaignModal = (campaign?: Campaign) => {
    if (campaign) {
      setEditingCampaign(campaign);
      setCampaignForm({
        id: campaign.id,
        platform: campaign.platform,
        url: campaign.url,
        title: campaign.title,
        target_amount: campaign.target_amount,
        description: campaign.description || '',
        public: campaign.public || false,
        // Конвертируем Milestone[] в проценты: target_amount / campaign.target_amount * 100
        milestones: campaign.milestones?.map(m => Math.round((m.target_amount / campaign.target_amount) * 100)) || [30, 50, 75, 100],
      });
    } else {
      setEditingCampaign(null);
      setCampaignForm({
        id: '',
        platform: 'manual',
        url: '',
        title: '',
        target_amount: 0,
        description: '',
        public: false,
        milestones: [30, 50, 75, 100],
      });
    }
    setCampaignModalOpen(true);
  };

  const handleSaveCampaign = () => {
    const currentCampaigns = config?.campaigns || [];
    // Конвертируем проценты в Milestone[] с правильными полями
    const milestones: Milestone[] = campaignForm.milestones.map((pct, idx) => ({
      id: `ms_${idx}`,
      title: `${pct}% цели`,
      target_amount: Math.round(campaignForm.target_amount * pct / 100),
      reached: false,
    }));

    const campaignData: Campaign = {
      ...campaignForm,
      milestones,
      current_amount: editingCampaign?.current_amount || 0,
      backers_count: editingCampaign?.backers_count || 0,
      days_left: editingCampaign?.days_left || 0,
    };

    let updatedCampaigns: Campaign[];
    if (editingCampaign) {
      updatedCampaigns = currentCampaigns.map(c => c.id === editingCampaign.id ? campaignData : c);
    } else {
      if (currentCampaigns.some(c => c.id === campaignForm.id)) {
        setMsg('Кампания с таким ID уже существует');
        return;
      }
      updatedCampaigns = [...currentCampaigns, campaignData];
    }

    updateCampaignsMutation.mutate(updatedCampaigns);
  };

  const handleDeleteCampaign = (campaignId: string) => {
    if (!window.confirm('Удалить эту кампанию?')) return;
    const currentCampaigns = config?.campaigns || [];
    const updatedCampaigns = currentCampaigns.filter(c => c.id !== campaignId);
    updateCampaignsMutation.mutate(updatedCampaigns);
  };

  const campaigns = config?.campaigns || [];
  const columns: Array<{ title: string; dataIndex?: string; key: string; width?: number; render?: (value: unknown, record: Campaign, index: number) => React.ReactNode }> = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 120 },
    { title: 'Название', dataIndex: 'title', key: 'title' },
    { title: 'Платформа', dataIndex: 'platform', key: 'platform', width: 80, render: (v: unknown) => <LTag color={v === 'planeta' ? 'blue' : v === 'boom' ? 'green' : 'default'}>{String(v)}</LTag> },
    { title: 'Цель', dataIndex: 'target_amount', key: 'target', width: 100, render: (v: unknown) => `${Number(v).toLocaleString('ru')} ₽` },
    { title: 'Публична', dataIndex: 'public', key: 'public', width: 80, render: (v: unknown) => v ? <LTag color="green">Да</LTag> : <LTag>Нет</LTag> },
    { title: 'Последняя проверка', dataIndex: 'last_checked', key: 'last_checked', width: 160, render: (v: unknown) => v ? new Date(String(v)).toLocaleString('ru') : '—' },
    { title: 'Ошибка', dataIndex: 'error', key: 'error', render: (v: unknown) => v ? <span style={{ color: '#cf1322', fontSize: 12 }}>{String(v)}</span> : '—' },
    {
      title: 'Действия', key: 'actions', width: 160,
      render: (_: unknown, record: Campaign) => (
        <LSpace>
          <LButton size="small" icon={<SettingOutlined />} onClick={() => openCampaignModal(record)}>Редакт.</LButton>
          <LButton size="small" danger icon={<SettingOutlined />} onClick={() => handleDeleteCampaign(record.id)}>Удалить</LButton>
        </LSpace>
      ),
    },
  ];

  return (
    <div>
      <LCard title="Управление" style={{ marginBottom: 24 }}>
        <LSpace>
          <LButton icon={<ReloadOutlined />} onClick={() => checkNowMutation.mutate()} loading={checkNowMutation.isPending}>Проверить сейчас</LButton>
          <LButton icon={<SettingOutlined />} onClick={showConfig}>Настройки мониторинга</LButton>
          <LButton type="primary" icon={<SettingOutlined />} onClick={() => openCampaignModal()}>Добавить кампанию</LButton>
        </LSpace>
        {msg && <div style={{ marginTop: 8, padding: '6px 12px', background: '#f0fdf4', borderRadius: 6, fontSize: 13 }}>{msg}</div>}
        <LCard title="Кампании" style={{ marginTop: 16 }}>
          <LTable columns={columns} dataSource={campaigns} rowKey="id" size="small" pagination={{ pageSize: 10 }} />
        </LCard>        <LModal title="Настройки краудфандинга" open={configModalOpen} onCancel={() => setConfigModalOpen(false)}
          footer={<LSpace><LButton onClick={() => setConfigModalOpen(false)}>Отмена</LButton><LButton type="primary" onClick={handleSaveConfig} loading={updateConfigMutation.isPending}>Сохранить</LButton></LSpace>}>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500, marginBottom: 4 }}><input type="checkbox" checked={formEnabled} onChange={e => setFormEnabled(e.target.checked)} /> Включено</label></div>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Интервал проверки (сек)</label><input type="number" min={60} max={86400} value={formInterval} onChange={e => setFormInterval(Number(e.target.value))} style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }} /></div>
        </LModal>        <LModal title={editingCampaign ? 'Редактировать кампанию' : 'Новая кампания'} open={campaignModalOpen} onCancel={() => setCampaignModalOpen(false)} width={600}
          footer={<LSpace><LButton onClick={() => setCampaignModalOpen(false)}>Отмена</LButton><LButton type="primary" onClick={handleSaveCampaign} loading={updateCampaignsMutation.isPending}>Сохранить</LButton></LSpace>}>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>ID *</label><input type="text" value={campaignForm.id} onChange={e => setCampaignForm({ ...campaignForm, id: e.target.value })} disabled={!!editingCampaign} style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }} placeholder="planeta_arkaim_2025" />{!editingCampaign && <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>Уникальный идентификатор (латиница, цифры, подчёркивания)</div>}</div>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Платформа *</label><select value={campaignForm.platform} onChange={e => setCampaignForm({ ...campaignForm, platform: e.target.value })} style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }}><option value="planeta">Planeta.ru</option><option value="boom">Boomstarter</option><option value="manual">Ручная (без парсинга)</option></select></div>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>URL *</label><input type="url" value={campaignForm.url} onChange={e => setCampaignForm({ ...campaignForm, url: e.target.value })} style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }} placeholder="https://planeta.ru/campaigns/..." /></div>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Название *</label><input type="text" value={campaignForm.title} onChange={e => setCampaignForm({ ...campaignForm, title: e.target.value })} style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }} placeholder="Издание книги &laquo;Наследие Аркаима&raquo;" /></div>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Цель (₽) *</label><input type="number" min={1} value={campaignForm.target_amount} onChange={e => setCampaignForm({ ...campaignForm, target_amount: Number(e.target.value) })} style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }} placeholder="500000" /></div>          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Описание для публичной страницы</label><textarea value={campaignForm.description} onChange={e => setCampaignForm({ ...campaignForm, description: e.target.value })} rows={3} style={{ width: '100%', padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', resize: 'vertical' }} placeholder="Описание целей сбора, что финансируется..." /></div>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500, marginBottom: 4 }}><input type="checkbox" checked={campaignForm.public} onChange={e => setCampaignForm({ ...campaignForm, public: e.target.checked })} /> Публиковать на вкладку &laquo;Кампании&raquo;</label><div style={{ fontSize: 12, color: '#999' }}>Непубличные кампании видны только в админке</div></div>
          <div style={{ marginBottom: 16 }}><label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Майлстоуны (% от цели)</label><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>{campaignForm.milestones.map((pct, idx) => (<div key={idx} style={{ display: 'flex', gap: 4, alignItems: 'center'}}><input type="number" min={1} max={100} value={pct} onChange={e => { const newMilestones = [...campaignForm.milestones]; newMilestones[idx] = Number(e.target.value); setCampaignForm({ ...campaignForm, milestones: newMilestones }); }} style={{ width: 60, padding: '4px 8px', border: '1px solid #d9d9d9', borderRadius: 6, fontSize: 13 }} /><span>%</span>{campaignForm.milestones.length > 1 && <LButton size="small" danger onClick={() => { const newMilestones = campaignForm.milestones.filter((_, i) => i !== idx); setCampaignForm({ ...campaignForm, milestones: newMilestones }); }}>×</LButton>}</div>))}<LButton size="small" icon={<SettingOutlined />} onClick={() => setCampaignForm({ ...campaignForm, milestones: [...campaignForm.milestones, 100] })}>Добавить</LButton></div><div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>Автоматически рассчитывают суммы в рублях</div></div>
        </LModal>
      </LCard>
    </div>
  );
}
function CrowdfundingContent() {
  const [historyCampaignId, setHistoryCampaignId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['crowdfunding'],
    queryFn: () => api.get<{ campaigns: Campaign[] }>('/book/crowdfunding/status'),
  });

  const campaigns = data?.campaigns || [];
  const totalRaised = campaigns.reduce((sum, c) => sum + c.current_amount, 0);
  const totalTarget = campaigns.reduce((sum, c) => sum + c.target_amount, 0);
  const totalBackers = campaigns.reduce((sum, c) => sum + c.backers_count, 0);

  const items = [
    {
      key: 'campaigns',
      label: 'Кампании',
      children: (
        <>
          <HeroSection />
          <LCard style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', gap: 24, justifyContent: 'center', flexWrap: 'wrap' }}>
              <LStatistic title="Кампаний" value={campaigns.length} />
              <LStatistic title="Всего собрано" value={totalRaised.toLocaleString('ru')} suffix="₽" />
              <LStatistic title="Общая цель" value={totalTarget.toLocaleString('ru')} suffix="₽" />
              <LStatistic title="Всего бэкеров" value={totalBackers} prefix={<UserOutlined />} />
            </div>
          </LCard>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: 48 }}><LSpin size="large" /></div>
          ) : campaigns.length === 0 ? (
            <LEmpty description="Нет активных кампаний" style={{ padding: 48 }} />
          ) : (
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              {campaigns.map(c => (
                <div key={c.id} style={{ flex: '1 1 45%', minWidth: 350 }}>
                  <CampaignCard campaign={c} onHistory={setHistoryCampaignId} />
                </div>
              ))}
            </div>
          )}
          <div style={{ textAlign: 'center', padding: '24px 0', color: '#94a3b8', fontSize: 13 }}>
            Каждый рубль помогает создать цифровое сознание книги
          </div>
        </>
      ),
    },
    {
      key: 'admin',
      label: 'Управление',
      children: <CrowdfundingAdminPanel />,
    },
  ];

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <LTabs items={items} />
      <CampaignHistoryModal campaignId={historyCampaignId || ''} open={!!historyCampaignId} onClose={() => setHistoryCampaignId(null)} />
    </div>
  );
}

export default function CrowdfundingPage() {
  return (
    <ProtectedRoute>
      <CrowdfundingContent />
    </ProtectedRoute>
  );
}
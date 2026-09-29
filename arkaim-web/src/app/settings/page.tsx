'use client';

import React, { useState } from 'react';
import { UserOutlined, BellOutlined, LockOutlined, BgColorsOutlined, DeleteOutlined, KeyOutlined, SaveOutlined, SafetyOutlined, GlobalOutlined, CommentOutlined, LikeOutlined, TeamOutlined, ThunderboltOutlined, CheckCircleOutlined, CloseCircleOutlined, CloudOutlined, DesktopOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { useAuth, useTheme } from '@/app/providers';
import { ProtectedRoute } from '@/shared/lib/guards';
import { LCard } from '@/shared/ui/light/LCard';
import { LInput } from '@/shared/ui/light/LInput';
import { LSwitch } from '@/shared/ui/light/LSwitch';
import { LButton } from '@/shared/ui/light/LButton';
import { LSelect } from '@/shared/ui/light/LSelect';
import { LDivider } from '@/shared/ui/light/LDivider';
import { LSpace } from '@/shared/ui/light/LSpace';
import { LTabs } from '@/shared/ui/light/LTabs';
import { LTag } from '@/shared/ui/light/LTag';
import { LAlert } from '@/shared/ui/light/LAlert';
import { LRadio } from '@/shared/ui/light/LRadio';

function AccountSettings() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(user?.display_name || '');
  const [msg, setMsg] = useState<string | null>(null);

  const updateMutation = useMutation({
    mutationFn: (values: { display_name: string }) => api.post('/auth/update-profile', values),
    onSuccess: () => { setMsg('Профиль обновлён'); queryClient.invalidateQueries({ queryKey: ['auth-user'] }); },
  });

  return (
    <LCard title={<><UserOutlined /> Аккаунт</>}>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 45%', minWidth: 200 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Имя пользователя</label>
          <LInput value={user?.username || ''} disabled />
        </div>
        <div style={{ flex: '1 1 45%', minWidth: 200 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Отображаемое имя</label>
          <LInput value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder="Как вас называть?" />
        </div>
      </div>

      <div style={{ marginTop: 12 }}>
        <span style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 4 }}>Провайдер</span>
        <LTag icon={<SafetyOutlined />} color="blue">{user?.provider || 'dev'}</LTag>
      </div>

      <div style={{ marginTop: 8, marginBottom: 16 }}>
        <span style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 4 }}>Роль</span>
        <LTag color={user?.role === 'admin' ? 'red' : user?.role === 'editor' ? 'blue' : 'green'}>
          {user?.role === 'admin' ? 'Администратор' : user?.role === 'editor' ? 'Редактор' : 'Читатель'}
        </LTag>
      </div>

      <LButton type="primary" icon={<SaveOutlined />} onClick={() => updateMutation.mutate({ display_name: displayName })} loading={updateMutation.isPending}>
        Сохранить
      </LButton>

      {msg && <div style={{ marginTop: 8, fontSize: 13, color: '#16a34a' }}>{msg}</div>}
    </LCard>
  );
}

function AppearanceSettings() {
  const { isDark, toggle } = useTheme();
  const [fontSize, setFontSize] = useState(() => {
    if (typeof window !== 'undefined') return localStorage.getItem('settings_font_size') || 'medium';
    return 'medium';
  });

  const handleFontChange = (value: string) => {
    setFontSize(value);
    localStorage.setItem('settings_font_size', value);
    document.documentElement.style.fontSize = value === 'small' ? '13px' : value === 'large' ? '17px' : '16px';
  };

  return (
    <LCard title={<><BgColorsOutlined /> Внешний вид</>}>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Тёмная тема</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <LSwitch checked={isDark} onChange={toggle} checkedChildren="Вкл" unCheckedChildren="Выкл" />
          <span style={{ fontSize: 12, color: '#999' }}>Переключает цветовую схему приложения</span>
        </div>
      </div>
      <div>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Размер шрифта</label>
        <LSelect value={fontSize} onChange={handleFontChange} options={[
          { value: 'small', label: 'Маленький' },
          { value: 'medium', label: 'Средний' },
          { value: 'large', label: 'Большой' },
        ]} style={{ width: 200 }} />
        <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>Размер текста в приложении</div>
      </div>
    </LCard>
  );
}

function LanguageSettings() {
  const [language, setLanguage] = useState(() => {
    if (typeof window !== 'undefined') return localStorage.getItem('settings_language') || 'ru';
    return 'ru';
  });

  const handleLanguageChange = (value: string) => {
    setLanguage(value);
    localStorage.setItem('settings_language', value);
  };

  return (
    <LCard title={<><GlobalOutlined /> Язык</>}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Язык интерфейса</label>
      <LSelect value={language} onChange={handleLanguageChange} options={[
        { value: 'ru', label: 'Русский' },
        { value: 'en', label: 'English' },
      ]} style={{ width: 200 }} />
      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>Язык отображения текста в приложении</div>
    </LCard>
  );
}

function NotificationSettings() {
  const getSetting = (key: string, defaultValue: boolean) => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('settings_notifications');
      if (saved) { const parsed = JSON.parse(saved); return parsed[key] !== undefined ? parsed[key] : defaultValue; }
    }
    return defaultValue;
  };

  const [emailEnabled, setEmailEnabled] = useState(() => getSetting('emailEnabled', true));
  const [pushEnabled, setPushEnabled] = useState(() => getSetting('pushEnabled', false));
  const [weeklyDigest, setWeeklyDigest] = useState(() => getSetting('weeklyDigest', true));
  const [chatNotifications, setChatNotifications] = useState(() => getSetting('chatNotifications', true));
  const [commentLiked, setCommentLiked] = useState(() => getSetting('commentLiked', true));
  const [commentAdded, setCommentAdded] = useState(() => getSetting('commentAdded', true));
  const [interpretationApproved, setInterpretationApproved] = useState(() => getSetting('interpretationApproved', true));
  const [interpretationRejected, setInterpretationRejected] = useState(() => getSetting('interpretationRejected', true));
  const [artifactApproved, setArtifactApproved] = useState(() => getSetting('artifactApproved', true));
  const [artifactRejected, setArtifactRejected] = useState(() => getSetting('artifactRejected', true));
  const [moderationQueue, setModerationQueue] = useState(() => getSetting('moderationQueue', true));
  const [msg, setMsg] = useState<string | null>(null);

  const handleSave = () => {
    localStorage.setItem('settings_notifications', JSON.stringify({
      emailEnabled, pushEnabled, weeklyDigest, chatNotifications,
      commentLiked, commentAdded, interpretationApproved, interpretationRejected,
      artifactApproved, artifactRejected, moderationQueue,
    }));
    setMsg('Настройки уведомлений сохранены');
  };

  function SwitchRow({ label, extra, checked, onChange }: { label: string; extra?: string; checked: boolean; onChange: (v: boolean) => void }) {
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <LSwitch checked={checked} onChange={onChange} />
          <span style={{ fontSize: 13 }}>{label}</span>
        </div>
        {extra && <div style={{ fontSize: 11, color: '#999', marginTop: 2, marginLeft: 48 }}>{extra}</div>}
      </div>
    );
  }

  return (
    <LCard title={<><BellOutlined /> Уведомления</>}>
      <LTabs
        items={[
          {
            key: 'general',
            label: 'Общие',
            children: (
              <div>
                <SwitchRow label="Email-уведомления" extra="Получать уведомления на email" checked={emailEnabled} onChange={setEmailEnabled} />
                <SwitchRow label="Push-уведомления" extra="Получать push-уведомления в приложении" checked={pushEnabled} onChange={setPushEnabled} />
                <SwitchRow label="Уведомления о чате" extra="Уведомления о новых ответах книги" checked={chatNotifications} onChange={setChatNotifications} />
                <SwitchRow label="Еженедельный дайджест" extra="Сводка активности за неделю" checked={weeklyDigest} onChange={setWeeklyDigest} />
              </div>
            ),
          },
          {
            key: 'community',
            label: <><TeamOutlined /> Сообщество</>,
            children: (
              <div>
                <p style={{ fontSize: 13, color: '#999', marginBottom: 16 }}>
                  Настройте уведомления о активности в сообществе
                </p>
                <LDivider plain><CommentOutlined /> Комментарии</LDivider>
                <SwitchRow label="Лайк на комментарий" extra="Когда кто-то поставил лайк вашему комментарию" checked={commentLiked} onChange={setCommentLiked} />
                <SwitchRow label="Новый комментарий" extra="Когда кто-то прокомментировал вашу интерпретацию или артефакт" checked={commentAdded} onChange={setCommentAdded} />
                <LDivider plain><LikeOutlined /> Интерпретации</LDivider>
                <SwitchRow label="Интерпретация одобрена" extra="Когда ваша интерпретация прошла модерацию" checked={interpretationApproved} onChange={setInterpretationApproved} />
                <SwitchRow label="Интерпретация отклонена" extra="Когда ваша интерпретация не прошла модерацию" checked={interpretationRejected} onChange={setInterpretationRejected} />
                <LDivider plain><TeamOutlined /> Артефакты</LDivider>
                <SwitchRow label="Артефакт одобрен" extra="Когда ваш артефакт прошёл модерацию" checked={artifactApproved} onChange={setArtifactApproved} />
                <SwitchRow label="Артефакт отклонён" extra="Когда ваш артефакт не прошёл модерацию" checked={artifactRejected} onChange={setArtifactRejected} />
                <LDivider plain><LockOutlined /> Модерация</LDivider>
                <SwitchRow label="Очередь модерации" extra="Уведомления о новомATERIAL на модерацию (для модераторов)" checked={moderationQueue} onChange={setModerationQueue} />
              </div>
            ),
          },
        ]}
      />
      <div style={{ marginTop: 16 }}>
        <LButton type="primary" icon={<SaveOutlined />} onClick={handleSave}>Сохранить</LButton>
      </div>
      {msg && <div style={{ marginTop: 8, fontSize: 13, color: '#16a34a' }}>{msg}</div>}
    </LCard>
  );
}

function SecuritySettings() {
  const queryClient = useQueryClient();
  const [newKey, setNewKey] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const { data: keys } = useQuery({
    queryKey: ['api-keys-settings'],
    queryFn: () => api.get<any[]>('/auth/api-keys'),
  });

  const { data: sessions } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.get<any[]>('/auth/admin/sessions'),
  });

  const generateMutation = useMutation({
    mutationFn: () => api.post<{ key: string }>('/auth/api-key'),
    onSuccess: (data) => { setNewKey(data.key); setMsg('API-ключ создан'); queryClient.invalidateQueries({ queryKey: ['api-keys-settings'] }); },
  });

  const deleteKeyMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/auth/api-keys/${id}`),
    onSuccess: () => { setMsg('Ключ удалён'); setConfirmDelete(null); queryClient.invalidateQueries({ queryKey: ['api-keys-settings'] }); },
  });

  const activeKeys = (keys || []).filter((k: any) => k.is_active);

  return (
    <LCard title={<><LockOutlined /> Безопасность</>}>
      <div style={{ marginBottom: 24 }}>
        <strong style={{ fontSize: 14 }}>API-ключи</strong>
        <p style={{ fontSize: 13, color: '#999', margin: '4px 0 12px' }}>
          Используйте ключи для программного доступа к API.
        </p>
        <LButton type="primary" icon={<KeyOutlined />} onClick={() => generateMutation.mutate()} loading={generateMutation.isPending}>
          Создать ключ
        </LButton>

        {newKey && (
          <LAlert type="success" title={<code>{newKey}</code>} description="Сохраните ключ — он показывается только один раз!" closable onClose={() => setNewKey(null)} style={{ marginTop: 12 }} />
        )}

        {activeKeys.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {activeKeys.map((item: any) => (
              <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                <KeyOutlined style={{ color: '#2563eb' }} />
                <div style={{ flex: 1 }}>
                  <code style={{ fontSize: 12 }}>{item.key_prefix}...</code>
                  <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                    {item.last_used_at ? `Последнее использование: ${new Date(item.last_used_at).toLocaleString('ru')}` : 'Не использован'}
                  </div>
                </div>
                {confirmDelete === item.id ? (
                  <LSpace>
                    <LButton size="small" onClick={() => deleteKeyMutation.mutate(item.id)} loading={deleteKeyMutation.isPending} danger>Удалить</LButton>
                    <LButton size="small" onClick={() => setConfirmDelete(null)}>Отмена</LButton>
                  </LSpace>
                ) : (
                  <LButton size="small" danger icon={<DeleteOutlined />} onClick={() => setConfirmDelete(item.id)} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <LDivider />

      <div>
        <strong style={{ fontSize: 14 }}>Активные сессии</strong>
        <p style={{ fontSize: 13, color: '#999', margin: '4px 0 12px' }}>
          Управление устройствами, на которых выполнен вход.
        </p>
        {sessions && sessions.length > 0 ? (
          <div>
            {sessions.slice(0, 5).map((item: any) => (
              <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid #f5f5f5' }}>
                <SafetyOutlined style={{ color: '#52c41a' }} />
                <div>
                  <span style={{ fontSize: 13 }}>Сессия {item.id?.slice(0, 8)}...</span>
                  <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                    Создана: {new Date(item.created_at).toLocaleString('ru')} · Истекает: {new Date(item.expires_at).toLocaleString('ru')}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <span style={{ fontSize: 13, color: '#999' }}>Информация о сессиях недоступна</span>
        )}
      </div>

      {msg && <div style={{ marginTop: 12, fontSize: 13, color: '#16a34a' }}>{msg}</div>}
    </LCard>
  );
}

function PrivacySettings() {
  const getSetting = (key: string, defaultValue: boolean) => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('settings_privacy');
      if (saved) { const parsed = JSON.parse(saved); return parsed[key] !== undefined ? parsed[key] : defaultValue; }
    }
    return defaultValue;
  };

  const [showProfile, setShowProfile] = useState(() => getSetting('showProfile', true));
  const [showHistory, setShowHistory] = useState(() => getSetting('showHistory', true));
  const [showTopics, setShowTopics] = useState(() => getSetting('showTopics', true));
  const [showActivity, setShowActivity] = useState(() => getSetting('showActivity', true));
  const [msg, setMsg] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleSave = () => {
    localStorage.setItem('settings_privacy', JSON.stringify({ showProfile, showHistory, showTopics, showActivity }));
    setMsg('Настройки конфиденциальности сохранены');
  };

  function SwitchRow({ label, extra, checked, onChange }: { label: string; extra?: string; checked: boolean; onChange: (v: boolean) => void }) {
    return (
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <LSwitch checked={checked} onChange={onChange} />
          <span style={{ fontSize: 13 }}>{label}</span>
        </div>
        {extra && <div style={{ fontSize: 11, color: '#999', marginTop: 2, marginLeft: 48 }}>{extra}</div>}
      </div>
    );
  }

  return (
    <LCard title="Конфиденциальность">
      <SwitchRow label="Показывать профиль другим" extra="Другие пользователи смогут видеть ваш профиль" checked={showProfile} onChange={setShowProfile} />
      <SwitchRow label="Показывать историю вопросов" extra="История будет видна в профиле" checked={showHistory} onChange={setShowHistory} />
      <SwitchRow label="Показывать изученные темы" extra="Темы будут видны в профиле" checked={showTopics} onChange={setShowTopics} />
      <SwitchRow label="Показывать активность в сообществе" extra="Ваша активность (лайки, комментарии) будет видна другим" checked={showActivity} onChange={setShowActivity} />
      <LButton type="primary" icon={<SaveOutlined />} onClick={handleSave}>Сохранить</LButton>

      {msg && <div style={{ marginTop: 8, fontSize: 13, color: '#16a34a' }}>{msg}</div>}

      <LDivider />
      {confirmDelete ? (
        <LSpace>
          <LButton danger onClick={() => { setConfirmDelete(false); setMsg('Запрос на удаление аккаунта отправлен'); }}>Подтвердить удаление</LButton>
          <LButton onClick={() => setConfirmDelete(false)}>Отмена</LButton>
        </LSpace>
      ) : (
        <LButton danger icon={<DeleteOutlined />} onClick={() => setConfirmDelete(true)}>Удалить аккаунт</LButton>
      )}
    </LCard>
  );
}

function GenerationSettings() {
  const queryClient = useQueryClient();
  const [mode, setMode] = React.useState<'local' | 'colab'>('local');
  const [colabUrl, setColabUrl] = React.useState('');
  const [msg, setMsg] = React.useState<string | null>(null);
  const [testResult, setTestResult] = React.useState<{ok: boolean; msg: string} | null>(null);

  // Load current config reactively
  const { data: config, isLoading: configLoading } = useQuery<{ url: string; is_local: boolean }>({
    queryKey: ['comfyui-config'],
    queryFn: () => api.get('/book/comfyui/config'),
    staleTime: 0,
  });

  const { data: status, isLoading: statusLoading } = useQuery<{ status: string; url?: string; error?: string }>({
    queryKey: ['comfyui-status'],
    queryFn: () => api.get('/book/comfyui/status'),
    refetchInterval: 30000,
    retry: false,
  });

  React.useEffect(() => {
    if (config) {
      setColabUrl(config.url || '');
      setMode(config.is_local ? 'local' : 'colab');
    }
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: (url: string) => api.post('/book/comfyui/config', { url }),
    onSuccess: () => {
      setMsg('URL ComfyUI сохранён');
      queryClient.invalidateQueries({ queryKey: ['comfyui-config'] });
      queryClient.invalidateQueries({ queryKey: ['comfyui-status'] });
    },
    onError: () => setMsg('Ошибка сохранения'),
  });

  const handleSave = () => {
    const url = mode === 'local' ? 'http://127.0.0.1:8188' : colabUrl.trim();
    if (!url) { setMsg('Введите URL туннеля'); return; }
    saveMutation.mutate(url);
  };

  const handleTest = () => {
    setTestResult(null);
    queryClient.invalidateQueries({ queryKey: ['comfyui-status'] });
    queryClient.refetchQueries({ queryKey: ['comfyui-status'] }).then(() => {
      if (status) {
        setTestResult(status.status === 'connected'
          ? { ok: true, msg: 'ComfyUI подключён' }
          : { ok: false, msg: status.error || 'ComfyUI недоступен' });
      } else {
        setTestResult({ ok: false, msg: 'Ошибка подключения' });
      }
    });
  };

  return (
    <LCard title={<><ThunderboltOutlined /> Генерация изображений</>}>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>Источник генерации</label>
        <LRadio value={mode} onChange={(v) => setMode(v as 'local' | 'colab')}>
          <LRadio.Button value="local"><DesktopOutlined /> Локальный ComfyUI</LRadio.Button>
          <LRadio.Button value="colab"><CloudOutlined /> Colab (Cloudflare Tunnel)</LRadio.Button>
        </LRadio>
      </div>

      {mode === 'local' && (
        <LAlert type="info" title="Локальный ComfyUI" description="Используется http://127.0.0.1:8188. Убедитесь, что ComfyUI запущен на вашем компьютере." showIcon style={{ marginBottom: 16 }} />
      )}

      {mode === 'colab' && (
        <>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 4 }}>URL туннеля Colab</label>
            <LInput value={colabUrl} onChange={e => setColabUrl(e.target.value)} placeholder="https://xxx.trycloudflare.com" prefix={<CloudOutlined />} />
            <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>Запустите notebooks/comfyui_colab.ipynb и скопируйте URL из последней ячейки</div>
          </div>
          <LAlert type="warning" title="Colab Free: T4 GPU, ~12ч/день, автоотключение через 90 мин бездействия" showIcon style={{ marginBottom: 16 }} />
        </>
      )}

      <LSpace>
        <LButton type="primary" icon={<SaveOutlined />} onClick={handleSave}>Сохранить</LButton>
<LButton icon={<CheckCircleOutlined />} onClick={handleTest} loading={statusLoading}>Проверить соединение</LButton>
      </LSpace>

      {msg && <div style={{ marginTop: 8, fontSize: 13, color: '#16a34a' }}>{msg}</div>}
      {status && status.status === 'connected' && (
        <div style={{ marginTop: 8, fontSize: 13, color: '#16a34a' }}>ComfyUI Online: {status.url}</div>
      )}
      {testResult && (
        <LAlert type={testResult.ok ? 'success' : 'error'} title={testResult.msg} showIcon style={{ marginTop: 12 }} />
      )}
    </LCard>
  );
}

function SettingsContent() {
  const items = [
    { key: 'account', label: <><UserOutlined /> Аккаунт</>, children: <AccountSettings /> },
    { key: 'appearance', label: <><BgColorsOutlined /> Внешний вид</>, children: <AppearanceSettings /> },
    { key: 'language', label: <><GlobalOutlined /> Язык</>, children: <LanguageSettings /> },
    { key: 'notifications', label: <><BellOutlined /> Уведомления</>, children: <NotificationSettings /> },
    { key: 'security', label: <><LockOutlined /> Безопасность</>, children: <SecuritySettings /> },
    { key: 'privacy', label: 'Конфиденциальность', children: <PrivacySettings /> },
    { key: 'generation', label: <><ThunderboltOutlined /> Генерация</>, children: <GenerationSettings /> },
  ];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ marginBottom: 16 }}>Настройки</h2>
      <LTabs items={items} />
    </div>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <SettingsContent />
    </ProtectedRoute>
  );
}
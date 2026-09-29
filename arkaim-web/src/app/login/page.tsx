'use client';

import { Suspense, useEffect, useState } from 'react';
import { CodeOutlined, SendOutlined } from '@ant-design/icons';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/app/providers';
import { LCard } from '@/shared/ui/light/LCard';
import { LButton } from '@/shared/ui/light/LButton';
import { LSpin } from '@/shared/ui/light/LSpin';
import { LDivider } from '@/shared/ui/light/LDivider';

function LoginPageInner() {
  const botUsername = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || 'ARKAIM_AI_Bot';
  const { user, establish } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [loginState, setLoginState] = useState<'idle' | 'loading' | 'success' | 'error'>(token ? 'loading' : 'idle');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (user && !token) {
      router.push('/profile');
    }
  }, [user, router, token]);

  useEffect(() => {
    if (!token) return;

    fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ token }),
    })
      .then(async (resp) => {
        const data = await resp.json();
        if (resp.ok && data.ok) {
          if (data.user?.id) establish(data.user);
          setLoginState('success');
          setTimeout(() => router.push('/profile'), 1500);
        } else {
          setLoginState('error');
          setErrorMsg(data.detail || 'Ошибка авторизации');
        }
      })
      .catch(() => {
        setLoginState('error');
        setErrorMsg('Не удалось подключиться к серверу');
      });
  }, [establish, token, router]);

  const [devLoading, setDevLoading] = useState(false);

  const handleDevLogin = async () => {
    setDevLoading(true);
    try {
      const resp = await fetch('/api/auth/dev-login', { method: 'POST' });
      const data = await resp.json();
      if (resp.ok && data.ok && data.user?.id) {
        establish(data.user);
        window.location.href = '/book';
      } else {
        alert(data.error || 'Ошибка dev-входа');
      }
    } catch {
      alert('Не удалось подключиться к серверу');
    } finally {
      setDevLoading(false);
    }
  };

  const handleBotLogin = () => {
    window.open(`https://t.me/${botUsername}?start=login`, '_blank');
  };

  if (loginState === 'loading') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
        <LCard style={{ maxWidth: 420, width: '100%', textAlign: 'center' }}>
          <LSpin size="large" />
          <div style={{ marginTop: 16 }}>Авторизация...</div>
        </LCard>
      </div>
    );
  }

  if (loginState === 'success') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
        <LCard style={{ maxWidth: 420, width: '100%', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
          <h3 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>Вход выполнен!</h3>
          <div style={{ color: '#999' }}>Перенаправление...</div>
        </LCard>
      </div>
    );
  }

  if (loginState === 'error') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
        <LCard style={{ maxWidth: 420, width: '100%', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16, color: '#ff4d4f' }}>✕</div>
          <h3 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>Ошибка входа</h3>
          <div style={{ color: '#999', marginBottom: 16 }}>{errorMsg}</div>
          <LButton type="primary" onClick={() => { setLoginState('idle'); router.push('/login'); }}>
            Попробовать снова
          </LButton>
        </LCard>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
      <LCard style={{ maxWidth: 420, width: '100%', textAlign: 'center' }}>
        <h3 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>Вход в систему</h3>
        <div style={{ color: '#999', marginBottom: 24 }}>Получите доступ к книге «Наследие Аркаима»</div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <LButton type="primary" icon={<SendOutlined />} size="large" onClick={handleBotLogin} style={{ width: '100%' }}>
            Войти через Telegram бота
          </LButton>
          <div style={{ fontSize: 12, color: '#999' }}>
            Отправьте команду /login боту @{botUsername}
          </div>

          <LDivider />

          <LButton icon={<CodeOutlined />} size="large" onClick={handleDevLogin} loading={devLoading} style={{ width: '100%' }}>
            Войти как разработчик
          </LButton>
        </div>

        <div style={{ marginTop: 24, textAlign: 'center', fontSize: 12 }}>
          <span style={{ color: '#999' }}>Нет аккаунта? </span>
          <Link href="/register">Зарегистрироваться</Link>
        </div>
      </LCard>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}><LSpin size="large" /></div>}>
      <LoginPageInner />
    </Suspense>
  );
}

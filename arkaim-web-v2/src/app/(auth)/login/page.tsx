/**
 * /login — вход (F1_SPEC §5). Telegram-виджет + email/dev — по фактическим контрактам.
 * Google OAuth скрыт (не настроен в backend; решение владельца).
 */
'use client';

import { Button, Card, Divider, Typography, App } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { doTelegramTokenLogin, doDevLogin, DEV_AUTH_ENABLED, useAuth } from '@/entities/auth/AuthProvider';
import { ApiError } from '@/shared/api';

export default function LoginPage() {
  const router = useRouter();
  const { message } = App.useApp();
  const { refresh } = useAuth();
  const [busy, setBusy] = useState(false);

  const handleTelegramToken = async (token: string) => {
    setBusy(true);
    try {
      await doTelegramTokenLogin(token);
      // Сбрасываем кэш /auth/me: иначе останется старый null (401) и MainLayout
      // сразу вернёт на /login, даже если cookie уже установлена.
      await refresh();
      router.replace('/');
    } catch (e) {
      message.error(e instanceof ApiError ? e.message : 'Ошибка входа');
      setBusy(false);
    }
  };

  const handleDev = async () => {
    setBusy(true);
    try {
      await doDevLogin('developer');
      await refresh();
      router.replace('/');
    } catch (e) {
      message.error(e instanceof ApiError ? e.message : 'Ошибка dev-входа');
      setBusy(false);
    }
  };

  // Telegram-виджет: контракт backend — /auth/telegram/callback (POST).
  // Токен из URL (?token=...) поддерживается /auth/telegram/login.
  const [urlToken] = useState(() =>
    typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('token') : null,
  );

  // B2 (F1-аудит §10): сетевой вызов ВЫНЕСЕН из render в useEffect.
  // ref-guard гарантирует однократный вызов даже при StrictMode
  // double-mount (одноразовый backend-токен — второй POST получил бы
  // «Токен недействителен»).
  const tokenHandledRef = useRef(false);
  useEffect(() => {
    if (!urlToken || tokenHandledRef.current || busy) return;
    tokenHandledRef.current = true;
    void handleTelegramToken(urlToken);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- handleTelegramToken и busy не в deps: вход должен сработать ровно один раз на mount
  }, [urlToken]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <Card title="Вход в «Наследие Аркаима»" style={{ width: 400 }}>
        <Typography.Paragraph type="secondary">
          Вход через Telegram-бота: отправьте /login боту, затем перейдите по выданной ссылке.
        </Typography.Paragraph>

        {urlToken && <Typography.Paragraph>Вход по ссылке из бота…</Typography.Paragraph>}

        <Divider>или</Divider>

        <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
          Регистрация по имени (email-провайдер backend):
        </Typography.Paragraph>
        <Link href="/register">
          <Button block>Зарегистрироваться</Button>
        </Link>

        {DEV_AUTH_ENABLED && (
          <>
            <Divider>dev</Divider>
            <Button block type="dashed" loading={busy} onClick={handleDev}>
              Войти как разработчик (dev)
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}

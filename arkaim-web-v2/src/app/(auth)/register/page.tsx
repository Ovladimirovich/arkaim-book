/**
 * /register — регистрация (POST /auth/register; создаёт reader; ставит cookie).
 */
'use client';

import { App, Button, Card, Form, Input, Typography } from 'antd';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { doRegister, useAuth } from '@/entities/auth/AuthProvider';
import { ApiError } from '@/shared/api';

interface FormValues {
  username: string;
  display_name?: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const { message } = App.useApp();
  const { refresh } = useAuth();
  const [busy, setBusy] = useState(false);

  const onFinish = async (v: FormValues) => {
    setBusy(true);
    try {
      await doRegister({ username: v.username.trim(), display_name: v.display_name?.trim() || undefined });
      message.success('Аккаунт создан');
      // Сбрасываем кэш /auth/me: иначе останется старый null (401) и MainLayout
      // сразу вернёт на /login, хотя cookie уже установлена.
      await refresh();
      router.replace('/');
    } catch (e) {
      const err = e as ApiError;
      message.error(err.message || 'Ошибка регистрации');
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <Card title="Регистрация" style={{ width: 420 }}>
        <Typography.Paragraph type="secondary">
          Имя пользователя (минимум 3 символа). Роль по умолчанию — читатель.
        </Typography.Paragraph>
        <Form<FormValues> layout="vertical" onFinish={onFinish}>
          <Form.Item
            name="username"
            label="Имя пользователя"
            rules={[
              { required: true, message: 'Введите имя' },
              { min: 3, message: 'Минимум 3 символа (контракт backend)' },
            ]}
          >
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item name="display_name" label="Отображаемое имя (необязательно)">
            <Input />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={busy}>
            Создать аккаунт
          </Button>
        </Form>
      </Card>
    </div>
  );
}

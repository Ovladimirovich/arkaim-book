'use client';

import { useState, useEffect } from 'react';
import { UserOutlined, MailOutlined, LockOutlined } from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/app/providers';
import { LCard } from '@/shared/ui/light/LCard';
import { LButton } from '@/shared/ui/light/LButton';

export default function RegisterPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [form, setForm] = useState({ username: '', display_name: '', email: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (user) router.push('/profile');
  }, [user, router]);

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!form.username || form.username.length < 3) errs.username = 'Минимум 3 символа';
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) errs.email = 'Некорректный email';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      const resp = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: form.username,
          display_name: form.display_name || form.username,
          email: form.email,
        }),
      });
      const data = await resp.json();
      if (resp.ok && data.ok) {
        setSuccess(true);
        setTimeout(() => router.push('/profile'), 1500);
      } else {
        alert(data.detail || data.error?.message || 'Ошибка регистрации');
      }
    } catch {
      alert('Не удалось подключиться к серверу');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
        <LCard style={{ maxWidth: 420, width: '100%', textAlign: 'center' }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✓</div>
          <h3 style={{ fontSize: 20, fontWeight: 600, marginBottom: 8 }}>Регистрация успешна!</h3>
          <div style={{ color: '#999' }}>Перенаправление...</div>
        </LCard>
      </div>
    );
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    fontSize: 14,
    border: '1px solid #d9d9d9',
    borderRadius: 6,
    outline: 'none',
    transition: 'border-color 0.2s',
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '80vh' }}>
      <LCard style={{ maxWidth: 420, width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <h3 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>Регистрация</h3>
          <div style={{ color: '#999' }}>Создайте аккаунт в «Наследие Аркаима»</div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Имя пользователя *</label>
            <div style={{ position: 'relative' }}>
              <UserOutlined style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#bfbfbf' }} />
              <input
                type="text"
                value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                placeholder="username"
                style={{ ...inputStyle, paddingLeft: 36 }}
              />
            </div>
            {errors.username && <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>{errors.username}</div>}
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Отображаемое имя</label>
            <div style={{ position: 'relative' }}>
              <UserOutlined style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#bfbfbf' }} />
              <input
                type="text"
                value={form.display_name}
                onChange={e => setForm({ ...form, display_name: e.target.value })}
                placeholder="Как вас называть?"
                style={{ ...inputStyle, paddingLeft: 36 }}
              />
            </div>
          </div>

          <div style={{ marginBottom: 24 }}>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4 }}>Email</label>
            <div style={{ position: 'relative' }}>
              <MailOutlined style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#bfbfbf' }} />
              <input
                type="email"
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                placeholder="your@email.com"
                style={{ ...inputStyle, paddingLeft: 36 }}
              />
            </div>
            {errors.email && <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>{errors.email}</div>}
          </div>

          <LButton type="primary" htmlType="submit" loading={loading} style={{ width: '100%', height: 40, fontSize: 16 }}>
            Зарегистрироваться
          </LButton>
        </form>

        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 14 }}>
          <span style={{ color: '#999' }}>Уже есть аккаунт? </span>
          <Link href="/login">Войти</Link>
        </div>
      </LCard>
    </div>
  );
}

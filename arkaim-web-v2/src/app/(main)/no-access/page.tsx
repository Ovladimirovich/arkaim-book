/**
 * /no-access — 403-экран (F1_SPEC §7).
 */
'use client';

import { Button, Result } from 'antd';
import { useRouter } from 'next/navigation';

export default function NoAccessPage() {
  const router = useRouter();
  return (
    <Result
      status="403"
      title="Недостаточно прав"
      subTitle="Этот раздел требует другой роли. Проверьте доступ у администратора."
      extra={
        <Button type="primary" onClick={() => router.push('/')}>
          На главную
        </Button>
      }
    />
  );
}

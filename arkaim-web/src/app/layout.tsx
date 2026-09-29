import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { AppShell } from '@/widgets/app-shell';
import { ServiceWorkerRegister } from '@/shared/ui/ServiceWorkerRegister';

export const metadata: Metadata = {
  title: 'Наследие Аркаима — Цифровое сознание книги',
  description: 'Интерактивный диалог с книгой «Наследие Аркаима». Задавайте вопросы, изучайте персонажей, открывайте скрытые смыслы.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <body>
        <ServiceWorkerRegister />
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}

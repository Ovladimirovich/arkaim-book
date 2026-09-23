import './globals.css';
import { Providers } from './providers';

export const metadata = {
  title: 'Наследие Аркаима — v2',
  description: 'Новый frontend — клиент текущего backend «Наследие Аркаима»',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" data-reading-theme="light">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

import Link from 'next/link';

export default function NotFound() {
  return (
    <div style={{ padding: 48, textAlign: 'center' }}>
      <h1 style={{ fontSize: 64, margin: 0 }}>404</h1>
      <p style={{ color: '#888' }}>Страница не найдена</p>
      <Link href="/">На главную</Link>
    </div>
  );
}

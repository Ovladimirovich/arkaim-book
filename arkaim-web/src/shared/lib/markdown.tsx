'use client';

import { Typography } from 'antd';

const { Text, Paragraph } = Typography;

/**
 * Простой markdown-рендерер для ответов книги.
 * Поддерживает: жирный, курсив, код, списки, ссылки.
 */
export function Markdown({ content }: { content: string }) {
  if (!content) return null;

  const lines = content.split('\n');

  return (
    <div style={{ color: '#e2e8f0' }}>
      {lines.map((line, i) => {
        // Пустая строка
        if (!line.trim()) return <div key={i} style={{ height: 8 }} />;

        // Списки
        if (line.match(/^[\s]*[-*]\s/)) {
          return <div key={i} style={{ paddingLeft: 16, color: '#e2e8f0' }}>• {renderInline(line.replace(/^[\s]*[-*]\s/, ''))}</div>;
        }
        if (line.match(/^[\s]*\d+\.\s/)) {
          return <div key={i} style={{ paddingLeft: 16, color: '#e2e8f0' }}>{renderInline(line.replace(/^[\s]*\d+\.\s/, ''))}</div>;
        }

        // Заголовки
        if (line.startsWith('### ')) return <Paragraph key={i} strong style={{ marginTop: 12, color: '#f1f5f9' }}>{renderInline(line.slice(4))}</Paragraph>;
        if (line.startsWith('## ')) return <Paragraph key={i} strong style={{ marginTop: 16, fontSize: '1.1em', color: '#f1f5f9' }}>{renderInline(line.slice(3))}</Paragraph>;
        if (line.startsWith('# ')) return <Paragraph key={i} strong style={{ marginTop: 20, fontSize: '1.2em', color: '#f1f5f9' }}>{renderInline(line.slice(2))}</Paragraph>;

        // Блоки кода
        if (line.startsWith('```')) return <div key={i} style={{ height: 4 }} />;

        // Обычный текст
        return <Paragraph key={i} style={{ margin: '2px 0', color: '#e2e8f0' }}>{renderInline(line)}</Paragraph>;
      })}
    </div>
  );
}

function renderInline(text: string) {
  // Жирный: **text**
  // Курсив: *text*
  // Код: `code`
  // Ссылки: [text](url)

  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining) {
    // Код
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`/);
    if (codeMatch) {
      if (codeMatch[1]) parts.push(<span key={key++} style={{ color: '#e2e8f0' }}>{codeMatch[1]}</span>);
      parts.push(<code key={key++} style={{ background: '#334155', padding: '1px 4px', borderRadius: 3, fontSize: '0.9em', color: '#93c5fd' }}>{codeMatch[2]}</code>);
      remaining = remaining.slice(codeMatch[0].length);
      continue;
    }

    // Жирный
    const boldMatch = remaining.match(/^(.*?)\*\*([^*]+)\*\*/);
    if (boldMatch) {
      if (boldMatch[1]) parts.push(<span key={key++} style={{ color: '#e2e8f0' }}>{boldMatch[1]}</span>);
      parts.push(<Text key={key++} strong style={{ color: '#f1f5f9' }}>{boldMatch[2]}</Text>);
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    // Курсив
    const italicMatch = remaining.match(/^(.*?)\*([^*]+)\*/);
    if (italicMatch) {
      if (italicMatch[1]) parts.push(<span key={key++} style={{ color: '#e2e8f0' }}>{italicMatch[1]}</span>);
      parts.push(<Text key={key++} italic style={{ color: '#cbd5e1' }}>{italicMatch[2]}</Text>);
      remaining = remaining.slice(italicMatch[0].length);
      continue;
    }

    // Ссылки
    const linkMatch = remaining.match(/^(.*?)\[([^\]]+)\]\(([^)]+)\)/);
    if (linkMatch) {
      if (linkMatch[1]) parts.push(<span key={key++}>{linkMatch[1]}</span>);
      parts.push(<a key={key++} href={linkMatch[3]} target="_blank" rel="noopener noreferrer">{linkMatch[2]}</a>);
      remaining = remaining.slice(linkMatch[0].length);
      continue;
    }

    // Остаток текста
    parts.push(<span key={key++} style={{ color: '#e2e8f0' }}>{remaining}</span>);
    break;
  }

  return parts;
}

/**
 * widgets/reading/ReadingContextActions.tsx — vtorichnye deystviya pri chlenii.
 */
'use client';

import type { Chapter } from '@/entities/reader/types';

interface Props {
  chapter: Chapter;
  onBackToList: () => void;
}

export function ReadingContextActions({ chapter, onBackToList }: Props) {
  const handleAsk = () => {
    const ctx = encodeURIComponent(
      `Глава "${chapter.title}". Спросить что-нибудь об этой главе.`,
    );
    window.location.href = `/ask?ask=${ctx}`;
  };

  const handleGenome = () => {
    window.location.href = '/library';
  };

  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        justifyContent: 'center',
        padding: '12px 16px',
        borderTop: '1px solid var(--reading-border)',
        background: 'var(--reading-surface)',
      }}
    >
      <button
        onClick={handleAsk}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 16px',
          border: '1px solid var(--reading-border)',
          borderRadius: 8,
          color: 'var(--reading-text)',
          fontSize: 13,
          fontWeight: 500,
          background: 'transparent',
          cursor: 'pointer',
          transition: 'background 0.15s, border-color 0.15s',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'var(--reading-hover)';
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--reading-accent)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--reading-border)';
        }}
      >
        💬 Спросить о главе
      </button>
      <button
        onClick={handleGenome}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 16px',
          border: '1px solid var(--reading-border)',
          borderRadius: 8,
          color: 'var(--reading-text)',
          fontSize: 13,
          fontWeight: 500,
          background: 'transparent',
          cursor: 'pointer',
          transition: 'background 0.15s, border-color 0.15s',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'var(--reading-hover)';
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--reading-accent)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--reading-border)';
        }}
      >
        📖 В геном
      </button>
      <button
        onClick={onBackToList}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 16px',
          border: '1px solid var(--reading-border)',
          borderRadius: 8,
          color: 'var(--reading-text-secondary)',
          fontSize: 13,
          fontWeight: 500,
          background: 'transparent',
          cursor: 'pointer',
          transition: 'background 0.15s, color 0.15s',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'var(--reading-hover)';
          (e.currentTarget as HTMLButtonElement).style.color = 'var(--reading-text)';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
          (e.currentTarget as HTMLButtonElement).style.color = 'var(--reading-text-secondary)';
        }}
      >
        ← Оглавление
      </button>
    </div>
  );
}

/**
 * widgets/reading/ReadingTOC.tsx — bokovoe oglavlenie / mobil'ny overlay.
 */
'use client';

import { useCallback } from 'react';
import Link from 'next/link';
import type { Chapter, ReadingProgressItem } from '@/entities/reader/types';

interface Props {
  chapters: Chapter[];
  progress?: ReadingProgressItem[];
  currentChapterId: string | null;
  onChapterClick: (chapter: Chapter) => void;
  onClose?: () => void;
  /** Mobile overlay mode — draws a backdrop and full-height panel. */
  mobile?: boolean;
}

export function ReadingTOC({ chapters, progress, currentChapterId, onChapterClick, onClose, mobile }: Props) {
  const started = new Map(progress?.map((p) => [p.chapter_id, p]) ?? []);

  const handleChapterClick = useCallback(
    (ch: Chapter) => {
      onChapterClick(ch);
      onClose?.();
    },
    [onChapterClick, onClose],
  );

  const containerStyle: React.CSSProperties = mobile
    ? {
        position: 'fixed',
        inset: 0,
        zIndex: 150,
        display: 'flex',
        background: 'rgba(0,0,0,0.5)',
      }
    : {
        width: 260,
        flexShrink: 0,
        overflowY: 'auto',
        borderRight: '1px solid var(--reading-border)',
        background: 'var(--reading-surface)',
      };

  const panelStyle: React.CSSProperties = mobile
    ? {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--reading-bg)',
      }
    : {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
      };

  return (
    <div style={containerStyle} onClick={mobile ? onClose : undefined}>
      <div
        style={panelStyle}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--reading-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span
            className="reading-ui"
            style={{ fontWeight: 600, fontSize: 14, color: 'var(--reading-text)' }}
          >
            Оглавление
          </span>
          {mobile && (
            <button
              onClick={onClose}
              aria-label="Закрыть оглавление"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 20,
                color: 'var(--reading-text-secondary)',
                padding: '4px 8px',
              }}
            >
              ×
            </button>
          )}
        </div>

        {/* Chapters */}
        <nav aria-label="Оглавление книги" style={{ flex: 1, overflowY: 'auto' }}>
          {chapters.map((ch, i) => {
            const isActive = ch.id === currentChapterId;
            const prog = started.get(ch.id);
            const completed = prog?.completed ?? false;
            const pct = prog ? Math.round(prog.scroll_percent) : 0;

            return (
              <button
                key={ch.id}
                onClick={() => handleChapterClick(ch)}
                aria-current={isActive ? 'true' : undefined}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 20px',
                  border: 'none',
                  background: isActive ? 'var(--reading-active)' : 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                  borderBottom: i < chapters.length - 1 ? `1px solid var(--reading-border)` : 'none',
                  transition: 'background 0.15s ease',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--reading-hover)';
                }}
                onMouseLeave={(e) => {
                  if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                }}
              >
                {/* Title */}
                <span
                  style={{
                    flex: 1,
                    fontSize: 14,
                    lineHeight: 1.4,
                    color: isActive ? 'var(--reading-accent)' : 'var(--reading-text)',
                    fontWeight: isActive ? 600 : 400,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {ch.title}
                </span>

                {/* Progress indicator */}
                {prog && (
                  <span
                    className="reading-ui"
                    style={{
                      fontSize: 11,
                      color: completed ? '#16a34a' : 'var(--reading-text-secondary)',
                      flexShrink: 0,
                      minWidth: 28,
                      textAlign: 'right',
                    }}
                  >
                    {completed ? '✓' : `${pct}%`}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Footer links */}
        <div
          className="reading-ui"
          style={{
            padding: '12px 20px',
            borderTop: '1px solid var(--reading-border)',
            display: 'flex',
            gap: 8,
            flexWrap: 'wrap',
          }}
        >
          <Link
            href="/"
            style={{
              fontSize: 12,
              color: 'var(--reading-text-secondary)',
              textDecoration: 'none',
              padding: '4px 8px',
              borderRadius: 4,
            }}
            onClick={onClose}
          >
            💬 Спросить книгу
          </Link>
          <Link
            href="/library"
            style={{
              fontSize: 12,
              color: 'var(--reading-text-secondary)',
              textDecoration: 'none',
              padding: '4px 8px',
              borderRadius: 4,
            }}
            onClick={onClose}
          >
            📖 Геном
          </Link>
          <Link
            href="/graph"
            style={{
              fontSize: 12,
              color: 'var(--reading-text-secondary)',
              textDecoration: 'none',
              padding: '4px 8px',
              borderRadius: 4,
            }}
            onClick={onClose}
          >
            🔗 Граф знаний
          </Link>
        </div>
      </div>
    </div>
  );
}

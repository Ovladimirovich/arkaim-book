/**
 * entities/reader/ChapterList.tsx — spisok glav s progressom.
 */
'use client';

import { useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getChapters, getReadingProgress, getReadingPosition } from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';
import type { Chapter } from '@/entities/reader/types';
import { ApiError } from '@/shared/api/errors';

interface Props {
  onChapterSelect: (chapter: Chapter) => void;
}

export function ChapterList({ onChapterSelect }: Props) {
  const chapters = useQuery({
    queryKey: ['book', 'chapters'],
    queryFn: () => getChapters(),
    staleTime: 5 * 60_000,
  });

  const progress = useQuery({
    queryKey: ['reader', 'progress'],
    queryFn: () => getReadingProgress(),
    staleTime: 60_000,
  });

  const position = useQuery({
    queryKey: ['reader', 'position'],
    queryFn: () => getReadingPosition(),
    staleTime: 60_000,
  });

  const startedMap = new Map(
    (progress.data?.data ?? []).map((p) => [p.chapter_id, p] as const),
  );

  const canContinue = position.data?.chapter_id != null;
  const continueChapter = canContinue
    ? (chapters.data ?? []).find((c) => c.id === position.data?.chapter_id)
    : undefined;

  const handleSelect = useCallback(
    (ch: Chapter) => {
      onChapterSelect(ch);
    },
    [onChapterSelect],
  );

  return (
    <div
      style={{
        maxWidth: 720,
        margin: '0 auto',
        padding: '32px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
      }}
    >
      {/* Header */}
      <div>
        <h1
          style={{
            fontFamily: 'Georgia, "Times New Roman", serif',
            fontSize: 32,
            fontWeight: 600,
            lineHeight: 1.2,
            margin: '0 0 8px',
            color: 'var(--reading-text)',
          }}
        >
          Наследие Аркаима
        </h1>
        <p
          className="reading-ui"
          style={{
            fontSize: 15,
            color: 'var(--reading-text-secondary)',
            margin: 0,
            lineHeight: 1.5,
          }}
        >
          Выберите главу для начала чтения. Прогресс сохраняется автоматически.
        </p>
      </div>

      {/* Continue card */}
      {canContinue && continueChapter && (
        <div
          style={{
            border: '1px solid var(--reading-accent)',
            borderRadius: 12,
            padding: 20,
            background: 'var(--reading-active)',
          }}
        >
          <p
            className="reading-ui"
            style={{
              fontSize: 12,
              color: 'var(--reading-text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              margin: '0 0 8px',
              fontWeight: 600,
            }}
          >
            Продолжить чтение
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <span
                style={{
                  fontFamily: 'Georgia, serif',
                  fontSize: 20,
                  fontWeight: 600,
                  color: 'var(--reading-text)',
                }}
              >
                {continueChapter.title}
              </span>
              {position.data?.scroll_percent != null && (
                <p
                  className="reading-ui"
                  style={{ fontSize: 13, color: 'var(--reading-text-secondary)', margin: '4px 0 0' }}
                >
                  На {Math.round(position.data.scroll_percent)}% главы
                </p>
              )}
            </div>
            <button
              onClick={() => handleSelect(continueChapter)}
              style={{
                padding: '10px 24px',
                background: 'var(--reading-accent)',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Продолжить
            </button>
          </div>
        </div>
      )}

      {/* Chapters list */}
      <StateView
        data={chapters.data}
        loading={chapters.isLoading}
        error={(chapters.error as ApiError | null) ?? null}
        onRetry={() => void chapters.refetch()}
        empty={chapters.data?.length === 0}
      >
        {(chs) => (
          <div
            style={{
              border: '1px solid var(--reading-border)',
              borderRadius: 12,
              overflow: 'hidden',
              background: 'var(--reading-surface)',
            }}
          >
            {chs.map((ch, i) => {
              const prog = startedMap.get(ch.id);
              const completed = prog?.completed ?? false;
              const pct = prog ? Math.round(prog.scroll_percent) : 0;

              return (
                <button
                  key={ch.id}
                  onClick={() => handleSelect(ch)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                    padding: '16px 20px',
                    border: 'none',
                    borderBottom: i < chs.length - 1 ? '1px solid var(--reading-border)' : 'none',
                    background: 'transparent',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.background = 'var(--reading-hover)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                  }}
                >
                  {/* Title */}
                  <span
                    style={{
                      flex: 1,
                      fontFamily: 'Georgia, serif',
                      fontSize: 17,
                      fontWeight: completed ? 500 : 600,
                      color: completed ? 'var(--reading-text-secondary)' : 'var(--reading-text)',
                      lineHeight: 1.4,
                    }}
                  >
                    {ch.title}
                  </span>

                  {/* Char count */}
                  <span
                    className="reading-ui"
                    style={{
                      fontSize: 12,
                      color: 'var(--reading-text-secondary)',
                      flexShrink: 0,
                    }}
                  >
                    {ch.char_count.toLocaleString('ru-RU')}
                  </span>

                  {/* Progress */}
                  {prog && (
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        minWidth: 80,
                        flexShrink: 0,
                      }}
                    >
                      <div
                        style={{
                          width: 48,
                          height: 4,
                          background: 'var(--reading-border)',
                          borderRadius: 2,
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${pct}%`,
                            height: '100%',
                            background: completed ? '#16a34a' : 'var(--reading-accent)',
                            borderRadius: 2,
                          }}
                        />
                      </div>
                      <span
                        className="reading-ui"
                        style={{
                          fontSize: 11,
                          color: completed ? '#16a34a' : 'var(--reading-text-secondary)',
                          minWidth: 24,
                        }}
                      >
                        {completed ? '✓' : `${pct}%`}
                      </span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </StateView>

      {/* Stats footer */}
      {progress.data?.stats && (
        <div
          className="reading-ui"
          style={{
            display: 'flex',
            gap: 24,
            justifyContent: 'center',
            fontSize: 13,
            color: 'var(--reading-text-secondary)',
          }}
        >
          <span>Начато: {progress.data.stats.chapters_started}</span>
          <span>Прочитано: {progress.data.stats.chapters_completed}</span>
          <span>
            {Math.round((progress.data.stats.total_seconds ?? 0) / 60)} мин
          </span>
        </div>
      )}
    </div>
  );
}

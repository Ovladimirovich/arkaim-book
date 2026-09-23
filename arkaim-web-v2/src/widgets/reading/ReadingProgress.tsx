/**
 * widgets/reading/ReadingProgress.tsx — progress bar i statistika chteniya.
 */
'use client';

import type { ReadingProgressItem, ReadingStats } from '@/entities/reader/types';

interface Props {
  progress?: ReadingProgressItem[];
  stats?: ReadingStats;
  currentChapterId: string;
  totalChapters: number;
}

export function ReadingProgress({ progress, stats, currentChapterId, totalChapters }: Props) {
  const completed = stats?.chapters_completed ?? 0;
  const pct = totalChapters > 0 ? Math.round((completed / totalChapters) * 100) : 0;
  const minutes = Math.round((stats?.total_seconds ?? 0) / 60);

  const currentProgress = progress?.find((p) => p.chapter_id === currentChapterId);
  const chapterPct = currentProgress ? Math.round(currentProgress.scroll_percent) : 0;

  return (
    <div
      className="reading-ui"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        padding: '8px 16px',
        fontSize: 12,
        color: 'var(--reading-text-secondary)',
        borderTop: '1px solid var(--reading-border)',
        background: 'var(--reading-surface)',
      }}
    >
      {/* Book-wide progress */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
        <span>Прогресс:</span>
        <div
          style={{
            flex: 1,
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
              background: 'var(--reading-accent)',
              borderRadius: 2,
              transition: 'width 0.3s ease',
            }}
          />
        </div>
        <span>{pct}% · {completed}/{totalChapters} гл.</span>
      </div>

      {/* Chapter progress */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <span>Глава:</span>
        <div
          style={{
            width: 60,
            height: 4,
            background: 'var(--reading-border)',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${chapterPct}%`,
              height: '100%',
              background: 'var(--reading-accent)',
              borderRadius: 2,
            }}
          />
        </div>
        <span>{chapterPct}%</span>
      </div>

      {/* Time */}
      <span style={{ flexShrink: 0 }}>{minutes} мин</span>
    </div>
  );
}

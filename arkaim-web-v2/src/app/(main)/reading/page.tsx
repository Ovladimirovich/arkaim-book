/**
 * /reading — Чтение книги (READING_UX_REDESIGN).
 *
 * Read-first surface Arkaim.
 *
 * Backend контракты (не меняются):
 *   GET /book/chapters
 *   GET /book/chapters/{chapter_id}   (текст выбранной главы — в ChapterReader)
 *   POST /book/reader/reading-event
 *   GET /book/reader/reading-progress
 *   GET /book/reader/reading-position
 *
 * Ключевое архитектурное правило:
 *   chapters query — один источник (ReadingPage).
 *   ChapterReader НЕ делает свой getChapters — это вызывает рекурсивный
 *   цикл обновлений через общий TanStack Query cache.
 *
 * selectedChapter ВЫЧИСЛЯЕТСЯ при рендере (useMemo), а не хранится в state:
 * setState внутри useEffect давал каскадные рендеры и
 * "Maximum update depth exceeded".
 */
'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { getChapters, getReadingPosition, type Chapter } from '@/shared/api';
import { ChapterList } from '@/entities/reader/ChapterList';
import { ChapterReader } from '@/entities/reader/ChapterReader';

export default function ReadingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const continueParam = searchParams.get('continue');

  // null/undefined/строка:
  //   undefined — выбор ещё не делался → автовыбор по позиции чтения;
  //   null      — читатель сознательно вернулся к списку глав;
  //   строка    — выбранная глава.
  const [selectedChapterId, setSelectedChapterId] = useState<string | null | undefined>(undefined);

  // Single source of truth for chapters — ChapterReader receives via props.
  const chaptersQuery = useQuery({
    queryKey: ['book', 'chapters'],
    queryFn: () => getChapters(),
    staleTime: 5 * 60_000,
  });

  const position = useQuery({
    queryKey: ['reader', 'position'],
    queryFn: () => getReadingPosition(),
    staleTime: 60_000,
  });

  // Determine which chapter to start with
  const initialChapterId = useMemo(() => {
    if (continueParam === '1') {
      return position.data?.chapter_id ?? chaptersQuery.data?.[0]?.id ?? null;
    }
    if (position.data?.chapter_id) {
      return position.data.chapter_id;
    }
    return null;
  }, [continueParam, position.data, chaptersQuery.data]);

  const resolvedChapterId = selectedChapterId === undefined ? initialChapterId : selectedChapterId;

  // selectedChapter ВЫЧИСЛЯЕТСЯ при рендере, а не хранится в state:
  // setState внутри useEffect давал каскадные рендеры
  // («Maximum update depth exceeded») и правило react-hooks/set-state-in-effect.
  const selectedChapter = useMemo(
    () =>
      resolvedChapterId
        ? (chaptersQuery.data?.find((c) => c.id === resolvedChapterId) ?? null)
        : null,
    [resolvedChapterId, chaptersQuery.data],
  );

  // Sync html[data-reading-theme] with the reading settings (overrides the static default).
  // Also reacts to system theme changes when settings.theme is 'auto'.
  useEffect(() => {
    const html = document.documentElement;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const resolve = () => {
      const raw = localStorage.getItem('arkaim_reading_settings');
      const parsed: { theme?: string } | null = raw ? (() => { try { return JSON.parse(raw); } catch { return null; } })() : null;
      const theme = parsed?.theme ?? 'auto';
      const effective = theme === 'auto' ? (mediaQuery.matches ? 'dark' : 'light') : theme;
      html.setAttribute('data-reading-theme', effective);
    };
    resolve();
    mediaQuery.addEventListener('change', resolve);
    return () => mediaQuery.removeEventListener('change', resolve);
  }, []);

  const isReadingMode = !!selectedChapter;

  const handleChapterSelect = useCallback((ch: Chapter) => {
    setSelectedChapterId(ch.id);
    router.replace('/reading', { scroll: false });
  }, [router]);

  const handleBackToList = useCallback(() => {
    setSelectedChapterId(null);
    router.replace('/reading', { scroll: false });
  }, [router]);

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        background: 'var(--reading-bg)',
      }}
    >
      {/* Desktop TOC sidebar */}
      {isReadingMode && chaptersQuery.data && (
        <aside
          style={{
            width: 260,
            flexShrink: 0,
            borderRight: '1px solid var(--reading-border)',
            background: 'var(--reading-surface)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <ReadingTOCDesktop
            chapters={chaptersQuery.data}
            currentChapterId={selectedChapter.id}
            onChapterClick={(ch) => handleChapterSelect(ch)}
          />
        </aside>
      )}

      {/* Main content */}
      <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {isReadingMode && selectedChapter ? (
          <ChapterReader
            key={selectedChapter.id}
            chapter={selectedChapter}
            chapters={chaptersQuery.data ?? []}
            onBackToList={handleBackToList}
            onChapterSelect={(chapterId) => setSelectedChapterId(chapterId)}
          />
        ) : (
          <ChapterList onChapterSelect={handleChapterSelect} />
        )}
      </main>
    </div>
  );
}

/** Desktop TOC inline component. */
function ReadingTOCDesktop({
  chapters,
  currentChapterId,
  onChapterClick,
}: {
  chapters: Chapter[];
  currentChapterId: string;
  onChapterClick: (ch: Chapter) => void;
}) {
  return (
    <nav aria-label="Оглавление" style={{ flex: 1, overflowY: 'auto' }}>
      {chapters.map((ch, i) => {
        const isActive = ch.id === currentChapterId;
        return (
          <button
            key={ch.id}
            onClick={() => onChapterClick(ch)}
            aria-current={isActive ? 'true' : undefined}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '12px 16px',
              border: 'none',
              borderBottom: i < chapters.length - 1 ? '1px solid var(--reading-border)' : 'none',
              background: isActive ? 'var(--reading-active)' : 'transparent',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={(e) => {
              if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'var(--reading-hover)';
            }}
            onMouseLeave={(e) => {
              if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            }}
          >
            <span
              className="reading-ui"
              style={{
                fontSize: 11,
                fontWeight: 600,
                color: isActive ? 'var(--reading-accent)' : 'var(--reading-text-secondary)',
                minWidth: 20,
                textAlign: 'center',
              }}
            >
              {i + 1}
            </span>
            <span
              style={{
                flex: 1,
                fontSize: 13,
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
          </button>
        );
      })}
    </nav>
  );
}

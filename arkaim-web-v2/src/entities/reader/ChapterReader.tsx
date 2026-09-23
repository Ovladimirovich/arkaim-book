/**
 * entities/reader/ChapterReader.tsx — read-first surface dlya odnoy glavy.
 */
'use client';

import { useRef, useCallback, useEffect, useMemo, memo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getChapter,
  recordReadingEvent,
  getReadingProgress,
  type Chapter,
} from '@/shared/api';
import { StateView } from '@/shared/ui/StateView';
import { useReadingSettings } from '@/shared/reading/useReadingSettings';
import { useReadingNavigation } from '@/shared/reading/useReadingNavigation';
import { ReadingTopbar } from '@/widgets/reading/ReadingTopbar';
import { ReadingProgress } from '@/widgets/reading/ReadingProgress';
import {
  columnWidthPx,
  paragraphSpacingPx,
  type ReadingSettings as ReadingSettingsType,
} from '@/entities/reader/types';

interface Props {
  chapter: Chapter;
  /** Chapters list — owned by ReadingPage to avoid duplicate queries. */
  chapters: Chapter[];
  onBackToList: () => void;
  /** Переключение на другую главу (Пред. / След.) — обновляет selectedChapterId в ReadingPage. */
  onChapterSelect: (chapterId: string) => void;
}

function computeScrollPercent(containerRef: React.RefObject<HTMLDivElement | null>): number {
  const el = containerRef.current;
  if (!el) return 0;
  // el.scrollTop / (scrollHeight - clientHeight) is the canonical
  // formula for "how far down has this element been scrolled".
  // Using el.clientHeight (not window.innerHeight) because the scrollable
  // container has its own fixed height (flex: 1, overflowY: auto).
  const total = el.scrollHeight - el.clientHeight;
  if (total <= 0) return 100;
  return Math.max(0, Math.min(100, Math.round((el.scrollTop / total) * 100)));
}

const ParagraphBlock = memo(function ParagraphBlock({
  text,
  settings,
}: {
  text: string;
  settings: ReadingSettingsType;
}) {
  const trimmed = text.trim();
  if (!trimmed) return null;
  return (
    <p
      style={{
        fontFamily: 'Georgia, "Times New Roman", serif',
        fontSize: settings.fontSize,
        lineHeight: settings.lineHeight,
        marginBottom: `${paragraphSpacingPx(settings.paragraphSpacing)}em`,
        textIndent: '2em',
        color: 'var(--reading-text)',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        marginTop: 0,
      }}
    >
      {trimmed}
    </p>
  );
});

export const ChapterReader = memo(function ChapterReader({ chapter, chapters, onBackToList, onChapterSelect }: Props) {
  const { settings, effectiveTheme, update, reset } = useReadingSettings();
  const qc = useQueryClient();

  // ReadingPage keeps html[data-reading-theme] in sync with reading settings + system preference.
  // ChapterReader reads the resolved value directly — no separate theme localStorage needed.
  const readingTheme = typeof document !== 'undefined'
    ? (document.documentElement.getAttribute('data-reading-theme') as 'light' | 'dark' | null) ?? 'light'
    : 'light';

  const chapterList = chapters ?? [];

  // ── Data queries ──
  // chapters — prop из ReadingPage; текст главы — ОДИН запрос
  // GET /book/chapters/{id}. /book/text непригоден для чтения главы:
  // он режет ГЛОБАЛЬНЫЙ текст всей книги, поэтому offset шагал по всей
  // книге, а автодозагрузка никогда не достигала «конца главы».
  const progressQuery = useQuery({
    queryKey: ['reader', 'progress'],
    queryFn: () => getReadingProgress(),
    staleTime: 60_000,
  });

  const contentQuery = useQuery({
    queryKey: ['book', 'chapter', chapter.id],
    queryFn: () => getChapter(chapter.id),
    staleTime: 10 * 60_000,
  });

  const content = contentQuery.data?.content ?? '';

  // ── Фронтmatter первой главы: распарсить «Автор: … Аннотация …» ────────
  /** Результат парсинга фронтmatter первой главы. */
  interface FrontMatter {
    author: string;
    annotation: string;
    rest: string;
  }

  const frontmatter = useMemo<FrontMatter | null>(() => {
    if (chapter.index !== 0 || !content) return null;
    // Шаблон: "Автор: <имя> Аннотация на книгу «...» <текст>"
    const m = content.match(
      /^Автор:\s*(.+?)\s+Аннотация[\s\S]*?(?=\n\n|\z)/,
    );
    if (!m) return null;
    const author = m[1].trim();
    const annotationRaw = m[0].replace(/^Автор:\s*.+?\s+/, '').trim();
    // Остаток — текст после аннотации (если есть пустая строка-разделитель)
    const afterIdx = content.indexOf('\n\n', m[0].length);
    const rest = afterIdx >= 0 ? content.slice(afterIdx + 2).trim() : '';
    return { author, annotation: annotationRaw, rest };
  }, [chapter.index, content]);

  const paragraphs = useMemo(() => {
    if (frontmatter) {
      // Для первой главы возвращаем парсерные блоки
      return [
        `Автор: ${frontmatter.author}`,
        frontmatter.annotation,
        ...(frontmatter.rest ? frontmatter.rest.split(/\n\n+/).filter(Boolean) : []),
      ];
    }
    return content.split(/\n\n+/).map((p) => p.trim()).filter(Boolean);
  }, [content, frontmatter]);

  const chapterIndex = chapterList.findIndex((c) => c.id === chapter.id);
  const navigation = useReadingNavigation(chapterList, chapterIndex);

  // ── Refs ──
  const containerRef = useRef<HTMLDivElement>(null);
  const readStartRef = useRef<number>(0);
  const scrollPercentRef = useRef(0);
  /** Событие чтения шлём, только если текст главы действительно открывали. */
  const contentLoadedRef = useRef(false);

  // ── Reset on chapter change ──
  useEffect(() => {
    readStartRef.current = Date.now();
    scrollPercentRef.current = 0;
    contentLoadedRef.current = false;
  }, [chapter.id]);

  useEffect(() => {
    if (content) {
      contentLoadedRef.current = true;
    }
  }, [content]);

  // ── Scroll tracking ──
  // Слушаем контейнер, а не window — прокручивается именно он (overflowY: auto).
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      scrollPercentRef.current = computeScrollPercent(containerRef);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);


  // ── Track reading event ──
  const trackRead = useMutation({
    mutationFn: (opts: { completed: boolean; scrollPercent: number }) =>
      recordReadingEvent({
        chapter_id: chapter.id,
        chapter_index: chapter.index,
        read_seconds: Math.round((Date.now() - readStartRef.current) / 1000),
        scroll_percent: opts.scrollPercent,
        completed: opts.completed,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['reader', 'progress'] });
      void qc.invalidateQueries({ queryKey: ['reader', 'position'] });
    },
  });

  // Актуальный trackRead для unmount-cleanup: объект useMutation
  // меняет идентичность на каждом рендере.
  const trackReadRef = useRef(trackRead);
  useEffect(() => {
    trackReadRef.current = trackRead;
  }, [trackRead]);

  const saveAndLeave = useCallback(
    (completed: boolean) => {
      trackReadRef.current.mutate({ completed, scrollPercent: scrollPercentRef.current });
    },
    [],
  );

  const handlePrevChapter = useCallback(() => {
    if (navigation.prev) {
      saveAndLeave(false);
      onChapterSelect(navigation.prev.id);
    }
  }, [navigation.prev, saveAndLeave, onChapterSelect]);

  const handleNextChapter = useCallback(() => {
    if (navigation.next) {
      saveAndLeave(false);
      onChapterSelect(navigation.next.id);
    }
  }, [navigation.next, saveAndLeave, onChapterSelect]);

  // ── Auto-save on unmount ──
  // deps ОБЯЗАТЕЛЬНЫ: без них cleanup выполнялся на каждый рендер, и
  // mutate() → setState мутации → рендер → cleanup → mutate() …
  // давало «Maximum update depth exceeded».
  useEffect(() => {
    return () => {
      if (!contentLoadedRef.current) return;
      const pct = scrollPercentRef.current;
      trackReadRef.current.mutate({ completed: pct >= 95, scrollPercent: pct });
    };
  }, [chapter.id]);

  const contentWidth = columnWidthPx(settings.fontSize);

  return (
    <div
      data-reading-theme={readingTheme}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: 'var(--reading-bg)',
        overflow: 'hidden',
      }}
    >
      {/* Topbar */}
      <ReadingTopbar
        currentChapter={chapter}
        chapters={chapterList}
        progress={progressQuery.data?.data}
        settings={settings}
        effectiveTheme={effectiveTheme}
        onSettingsChange={update}
        onSettingsReset={reset}
        onChapterClick={() => {
          saveAndLeave(false);
          onBackToList();
        }}
      />

      {/* Reading surface */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          justifyContent: 'center',
          scrollBehavior: 'smooth',
        }}
        className="reading-scroll"
      >
        <article
          style={{
            width: '100%',
            maxWidth: contentWidth,
            padding: '40px 32px 80px',
          }}
        >
          {/* Chapter title */}
          <header style={{ marginBottom: 32 }}>
            <h1
              style={{
                fontFamily: 'Georgia, "Times New Roman", serif',
                fontSize: 28,
                fontWeight: 600,
                lineHeight: 1.3,
                textAlign: 'center',
                color: 'var(--reading-text)',
                marginTop: 0,
                marginBottom: 8,
              }}
            >
              {chapter.index === 0 ? 'Наследие Аркаима' : chapter.title}
            </h1>
            <p
              className="reading-ui"
              style={{
                textAlign: 'center',
                fontSize: 13,
                color: 'var(--reading-text-secondary)',
                margin: 0,
              }}
            >
              {chapter.char_count.toLocaleString('ru-RU')} символов
            </p>
          </header>

          {/* Text */}
          <StateView
            data={content ? paragraphs : undefined}
            loading={contentQuery.isLoading}
            error={
              contentQuery.error instanceof Error
                ? { message: contentQuery.error.message }
                : null
            }
            onRetry={() => void contentQuery.refetch()}
            empty={!contentQuery.data && !contentQuery.isLoading && !contentQuery.error}
          >
            {(data) => (
              <div>
                {data.map((para, i) => {
                  // Фронтmatter: первая строка — автор, вторая — аннотация
                  if (frontmatter && i === 0) {
                    const m = para.match(/^(Автор:\s*)(.+)$/);
                    if (m) {
                      return (
                        <p key={`${chapter.id}-${i}`} style={{
                          fontFamily: 'Georgia, "Times New Roman", serif',
                          fontSize: settings.fontSize,
                          lineHeight: settings.lineHeight,
                          marginBottom: `${paragraphSpacingPx(settings.paragraphSpacing)}em`,
                          textAlign: 'center',
                          color: 'var(--reading-text-secondary)',
                          marginTop: 0,
                        }}>
                          <span style={{ fontWeight: 600 }}>{m[1]}</span>{m[2]}
                        </p>
                      );
                    }
                  }
                  if (frontmatter && i === 1) {
                    return (
                      <p key={`${chapter.id}-${i}`} style={{
                        fontFamily: 'Georgia, "Times New Roman", serif',
                        fontSize: settings.fontSize,
                        lineHeight: settings.lineHeight,
                        marginBottom: `${paragraphSpacingPx(settings.paragraphSpacing)}em`,
                        fontStyle: 'italic',
                        color: 'var(--reading-text-secondary)',
                        textIndent: 0,
                        marginTop: 0,
                        padding: '8px 16px',
                        borderLeft: '3px solid var(--reading-accent)',
                        background: 'var(--reading-surface)',
                      }}>
                        Аннотация:{' '}
                        {para.replace(/^Аннотация(?:\s*на книгу «[^»]+»)?\s*/i, '')}
                      </p>
                    );
                  }
                  return <ParagraphBlock key={`${chapter.id}-${i}`} text={para} settings={settings} />;
                })}
              </div>
            )}
          </StateView>

          {/* Chapter end */}
          {content && (
            <div
              style={{
                textAlign: 'center',
                padding: '32px 0',
                borderTop: '1px solid var(--reading-border)',
                marginTop: 32,
              }}
            >
              <span
                className="reading-ui"
                style={{ fontSize: 12, color: 'var(--reading-text-secondary)' }}
              >
                · · ·
              </span>
              <p
                className="reading-ui"
                style={{
                  fontSize: 12,
                  color: 'var(--reading-text-secondary)',
                  marginTop: 8,
                  marginBottom: 0,
                }}
              >
                Конец главы
              </p>
            </div>
          )}
        </article>
      </div>

      {/* Bottom nav */}
      <nav
        className="reading-ui"
        style={{
          height: 'var(--reading-nav-height)',
          borderTop: '1px solid var(--reading-border)',
          background: 'var(--reading-surface)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          gap: 12,
        }}
        aria-label="Навигация по главам"
      >
        <button
          onClick={handlePrevChapter}
          disabled={!navigation.prev}
          aria-label="Предыдущая глава"
          style={{
            padding: '8px 16px',
            border: '1px solid var(--reading-border)',
            borderRadius: 6,
            background: navigation.prev ? 'transparent' : 'var(--reading-hover)',
            color: navigation.prev ? 'var(--reading-text)' : 'var(--reading-text-secondary)',
            cursor: navigation.prev ? 'pointer' : 'not-allowed',
            fontSize: 13,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path
              d="M8 10L4 6l4-4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Пред.
        </button>

        <span
          style={{
            fontSize: 13,
            color: 'var(--reading-text-secondary)',
            fontWeight: 500,
          }}
        >
          {chapters?.length ?? '?'} глав
        </span>

        <button
          onClick={handleNextChapter}
          disabled={!navigation.next}
          aria-label="Следующая глава"
          style={{
            padding: '8px 16px',
            border: '1px solid var(--reading-border)',
            borderRadius: 6,
            background: navigation.next ? 'var(--reading-accent)' : 'var(--reading-hover)',
            color: navigation.next ? '#fff' : 'var(--reading-text-secondary)',
            cursor: navigation.next ? 'pointer' : 'not-allowed',
            fontSize: 13,
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
        >
          След.
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path
              d="M4 2l4 4-4 4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </nav>

      {/* Progress bar */}
      <ReadingProgress
        progress={progressQuery.data?.data}
        stats={progressQuery.data?.stats}
        currentChapterId={chapter.id}
        totalChapters={chapters?.length ?? 0}
      />
    </div>
  );
});

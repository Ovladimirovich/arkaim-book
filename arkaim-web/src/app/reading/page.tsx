'use client';

import { useState, useEffect, useRef } from 'react';
import { LCard, LTag, LEmpty, LSpin, LSpace, LButton, LDivider, LSegmented } from '@/shared/ui/light';
import { BookOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';
import { StateView } from '@/shared/ui/StateView';
import { useIsMobile } from '@/shared/lib/hooks';

type ChapterMeta = {
  id: string;
  title: string;
  char_count: number;
  index: number;
  section_type?: 'title' | 'prologue' | 'part' | 'epilogue';
};

type ChapterFull = ChapterMeta & {
  content: string;
};

const FONT_SIZES = [
  { label: 'Маленький', value: 14 },
  { label: 'Средний', value: 16 },
  { label: 'Большой', value: 18 },
  { label: 'Очень большой', value: 20 },
];

// ── TOC helpers ──────────────────────────────────────────────

function tocsLabel(ch: ChapterMeta): string {
  if (ch.section_type === 'title') return 'Титульная страница';
  return ch.title;
}

function tocsSize(ch: ChapterMeta): string {
  const k = Math.round(ch.char_count / 1000);
  return `${k}k`;
}

// ── Section styling ──────────────────────────────────────────

function sectionClass(ch: ChapterFull): string {
  if (ch.section_type === 'title') return 'section-title-page';
  if (ch.section_type === 'prologue') return 'section-prologue';
  if (ch.section_type === 'epilogue') return 'section-epilogue';
  return 'section-part';
}

/**
 * Титульная страница: первый чанк реального текста содержит «Автор: …» и
 * «Аннотация на книгу …», слитые в один абзац. Разделяем их для отображения,
 * не меняя сам текст. Если маркеры не найдены — текст показывается как есть.
 */
const AUTHOR_MARK = 'Автор: ОВладимирович';
const ANNOTATION_MARK = 'Аннотация на книгу «Наследие Аркаима»';

function splitTitlePage(content: string): { author: string | null; annotation: string | null; rest: string } {
  let rest = content.trim();
  let author: string | null = null;
  let annotation: string | null = null;
  if (rest.startsWith(AUTHOR_MARK)) {
    author = AUTHOR_MARK;
    rest = rest.slice(AUTHOR_MARK.length).trim();
  }
  if (rest.startsWith(ANNOTATION_MARK)) {
    annotation = ANNOTATION_MARK;
    rest = rest.slice(ANNOTATION_MARK.length).trim();
  }
  return { author, annotation, rest };
}

// ── ReadingView ──────────────────────────────────────────────

function ReadingView({ chapter, fontSize }: { chapter: ChapterFull; fontSize: number }) {
  const isTitle = chapter.section_type === 'title';
  const isPrologue = chapter.section_type === 'prologue';
  const isEpilogue = chapter.section_type === 'epilogue';

  return (
    <div
      className={sectionClass(chapter)}
      style={{
        maxWidth: 680,
        margin: '0 auto',
        padding: isTitle ? '48px 0 40px' : '0 0 40px',
      }}
    >
      {/* Титульная страница — без номера части, без заголовка-«Часть 0» */}
      {isTitle ? (
        (() => {
          const { author, annotation, rest } = splitTitlePage(chapter.content);
          return (
            <div style={{ padding: '24px 0' }}>
              {author && (
                <p style={{ textAlign: 'center', fontSize: Math.round(fontSize * 1.05), lineHeight: 1.8, color: 'var(--foreground)', fontWeight: 500, marginBottom: 28 }}>
                  {author}
                </p>
              )}
              {annotation && (
                <h2 style={{ textAlign: 'center', fontSize: Math.round(fontSize * 1.25), lineHeight: 1.6, color: 'var(--foreground)', fontWeight: 600, marginBottom: 28 }}>
                  {annotation}
                </h2>
              )}
              <div>
                {rest.split('\n\n').map((paragraph, i) => (
                  <p key={i} style={{ fontSize, lineHeight: 1.9, marginBottom: '1.4em', textIndent: '2em', color: 'var(--foreground)' }}>
                    {paragraph}
                  </p>
                ))}
              </div>
            </div>
          );
        })()
      ) : (
        <>
          {/* Заголовок: пролог, части, эпилог */}
          <h2
            style={{
              marginBottom: 28,
              textAlign: 'center',
              lineHeight: 1.5,
              fontSize: isPrologue || isEpilogue ? 26 : 24,
              fontWeight: isPrologue || isEpilogue ? 600 : 500,
              color: 'var(--foreground)',
              letterSpacing: isPrologue || isEpilogue ? 0.5 : 0,
            }}
          >
            {chapter.title}
          </h2>

          <LDivider />

          <div>
            {chapter.content.split('\n\n').map((paragraph, i) => (
              <p
                key={i}
                style={{
                  fontSize,
                  lineHeight: 1.85,
                  marginBottom: '1.3em',
                  textIndent: '2em',
                  margin: '0 0 1.3em 0',
                  color: 'var(--foreground)',
                }}
              >
                {paragraph}
              </p>
            ))}
          </div>
        </>
      )}

      <LDivider />

      <div style={{ textAlign: 'center', marginTop: 32 }}>
        <span style={{ fontSize: 12, color: 'var(--muted-fg)' }}>Конец раздела</span>
      </div>
    </div>
  );
}

function ReadingContent() {
  const [chapterIndex, setChapterIndex] = useState(0);
  const [fontSize, setFontSize] = useState(16);
  // На мобильном оглавление (260px, flexShrink: 0) вместе с панелью размера текста
  // расширяло ряд за пределы вьюпорта — на узких экранах оно свёрнуто по умолчанию,
  // как и в «Чате с книгой» (там такой же паттерн через useIsMobile).
  const isMobile = useIsMobile();
  const [showToc, setShowToc] = useState(true);
  const contentRef = useRef<HTMLDivElement>(null);

  const { data: chaptersData, isLoading: chaptersLoading, isError: chaptersIsError, error: chaptersError, refetch: refetchChapters } = useQuery({
    queryKey: ['chapters'],
    queryFn: () => api.get<{ ok: boolean; data: ChapterMeta[]; total: number }>('/book/chapters'),
  });

  const chapters: ChapterMeta[] = chaptersData?.data || [];
  const currentChapter = chapters[chapterIndex];

  const { data: chapterData, isLoading: chapterLoading, isError: chapterIsError, error: chapterError, refetch: refetchChapter } = useQuery({
    queryKey: ['chapter', currentChapter?.id],
    queryFn: () => api.get<{ ok: boolean; data: ChapterFull }>(`/book/chapters/${currentChapter?.id}`),
    enabled: !!currentChapter?.id,
  });

  const retryReading = () => {
    void refetchChapters();
    if (currentChapter?.id) void refetchChapter();
  };

  const chapterContent: ChapterFull | undefined = chapterData?.data;

  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [chapterIndex]);

  const prevChapter = () => { if (chapterIndex > 0) setChapterIndex(chapterIndex - 1); };
  const nextChapter = () => { if (chapterIndex < chapters.length - 1) setChapterIndex(chapterIndex + 1); };

  if (chaptersIsError) {
    return (
      <StateView
        state="error"
        title="Не удалось загрузить содержание книги"
        description={
          chaptersError instanceof Error
            ? `Сервер ответил ошибкой: ${chaptersError.message}. Текст глав недоступен, фиктивное содержание не показывается.`
            : 'Проверьте связь с сервером и повторите попытку.'
        }
        onRetry={retryReading}
      />
    );
  }

  if (chaptersLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
        <LSpin size="large" tip="Загрузка содержания..." />
      </div>
    );
  }

  if (chapters.length === 0) {
    return <LEmpty description="Содержание книги не найдено" />;
  }

  return (
    <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 100px)' }}>
      {showToc && !isMobile && (
        <div style={{ width: 260, flexShrink: 0, overflow: 'auto' }}>
          <LCard size="small" title={<><BookOutlined /> Содержание</>} extra={<LTag>{chapters.length}</LTag>} style={{ marginBottom: 8 }}>
            {chapters.map((item, i) => (
              <div key={item.id}
                style={{ cursor: 'pointer', background: i === chapterIndex ? 'var(--accent-soft)' : undefined, borderRadius: 4, padding: '6px 8px', display: 'flex', alignItems: 'center' }}
                onClick={() => setChapterIndex(i)}
              >
                <span style={{ fontSize: 12, color: i === chapterIndex ? 'var(--accent)' : undefined, flex: 1, fontWeight: item.section_type === 'part' ? 500 : 400 }}>
                  {tocsLabel(item)}
                </span>
                <span style={{ fontSize: 10, color: 'var(--muted-fg)', marginLeft: 'auto' }}>
                  {tocsSize(item)}
                </span>
              </div>
            ))}
          </LCard>

          <LCard size="small" title="Навигация">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <a href="/library" style={{ fontSize: 12 }}>📖 Библиотека</a>
              <a href="/book" style={{ fontSize: 12 }}>💬 Задать вопрос</a>
              <a href="/genres" style={{ fontSize: 12 }}>🏷 Жанры</a>
            </div>
          </LCard>
        </div>
      )}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* flexWrap + gap: на узких экранах панель «Скрыть оглавление / Размер» не переносилась
            и вылезала за границу вьюпорта (горизонтальный overflow). */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
          <LSpace>
            <LButton size="small" onClick={() => setShowToc(!showToc)}>
              {showToc && !isMobile ? 'Скрыть оглавление' : 'Показать оглавление'}
            </LButton>
          </LSpace>
          {/* maxWidth + wrap: подпись «Размер» и сегмент-контрол (несжимаемый, ~331px)
              вместе выходили за вьюпорт на 375px. */}
          <LSpace style={{ flexWrap: 'wrap', maxWidth: '100%' }}>
            <span style={{ fontSize: 12, color: 'var(--muted-fg)' }}>Размер:</span>
            <LSegmented
              size="small"
              options={FONT_SIZES.map(f => ({ label: f.label, value: f.value }))}
              value={fontSize}
              onChange={(v) => setFontSize(v as number)}
            />
          </LSpace>
        </div>

        <LCard size="small" ref={contentRef} style={{ flex: 1, overflow: 'auto' }}>
          <div style={{ padding: '24px 32px' }}>
            {chapterLoading ? (
              <div style={{ textAlign: 'center', padding: 48 }}><LSpin /></div>
            ) : chapterIsError ? (
              <StateView
                state="error"
                title="Не удалось загрузить главу"
                description={
                  chapterError instanceof Error
                    ? `Сервер ответил ошибкой: ${chapterError.message}. Текст главы недоступен.`
                    : 'Проверьте связь с сервером и повторите попытку.'
                }
                onRetry={() => { void refetchChapter(); }}
              />
            ) : chapterContent ? (
              <ReadingView chapter={chapterContent} fontSize={fontSize} />
            ) : (
              <LEmpty description="Глава не найдена" />
            )}
          </div>
        </LCard>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
          <LButton icon={<LeftOutlined />} onClick={prevChapter} disabled={chapterIndex === 0}>
            Предыдущая
          </LButton>
          <span style={{ fontSize: 12, color: 'var(--muted-fg)' }}>
            {chapterIndex + 1} / {chapters.length}
          </span>
          <LButton onClick={nextChapter} disabled={chapterIndex === chapters.length - 1}>
            Следующая <RightOutlined />
          </LButton>
        </div>
      </div>
    </div>
  );
}

export default function ReadingPage() {
  return (
    <ProtectedRoute>
      <ReadingContent />
    </ProtectedRoute>
  );
}
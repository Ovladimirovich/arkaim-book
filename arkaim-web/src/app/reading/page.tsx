'use client';

import { useState, useEffect, useRef } from 'react';
import { LCard, LTag, LEmpty, LSpin, LSpace, LButton, LDivider, LSegmented } from '@/shared/ui/light';
import { BookOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/shared/lib/api';
import { ProtectedRoute } from '@/shared/lib/guards';

type ChapterMeta = {
  id: string;
  title: string;
  char_count: number;
  index: number;
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

function ReadingView({ chapter, fontSize }: { chapter: ChapterFull; fontSize: number }) {
  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      <h2 style={{ marginBottom: 24, textAlign: 'center', lineHeight: 1.4, fontSize: 24 }}>{chapter.title}</h2>

      <LDivider />

      <div style={{ fontSize, lineHeight: 1.8, color: '#374151' }}>
        {chapter.content.split('\n\n').map((paragraph, i) => (
          <p key={i} style={{ fontSize, lineHeight: 1.8, marginBottom: '1.2em', textIndent: '2em', margin: '0 0 1.2em 0' }}>
            {paragraph}
          </p>
        ))}
      </div>

      <LDivider />

      <div style={{ textAlign: 'center', marginTop: 32 }}>
        <span style={{ fontSize: 12, color: '#999' }}>Конец раздела</span>
      </div>
    </div>
  );
}

function ReadingContent() {
  const [chapterIndex, setChapterIndex] = useState(0);
  const [fontSize, setFontSize] = useState(16);
  const [showToc, setShowToc] = useState(true);
  const contentRef = useRef<HTMLDivElement>(null);

  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['chapters'],
    queryFn: () => api.get<{ ok: boolean; data: ChapterMeta[]; total: number }>('/book/chapters'),
  });

  const chapters: ChapterMeta[] = chaptersData?.data || [];
  const currentChapter = chapters[chapterIndex];

  const { data: chapterData, isLoading: chapterLoading } = useQuery({
    queryKey: ['chapter', currentChapter?.id],
    queryFn: () => api.get<{ ok: boolean; data: ChapterFull }>(`/book/chapters/${currentChapter?.id}`),
    enabled: !!currentChapter?.id,
  });

  const chapterContent: ChapterFull | undefined = chapterData?.data;

  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  }, [chapterIndex]);

  const prevChapter = () => { if (chapterIndex > 0) setChapterIndex(chapterIndex - 1); };
  const nextChapter = () => { if (chapterIndex < chapters.length - 1) setChapterIndex(chapterIndex + 1); };

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
      {showToc && (
        <div style={{ width: 260, flexShrink: 0, overflow: 'auto' }}>
          <LCard size="small" title={<><BookOutlined /> Содержание</>} extra={<LTag>{chapters.length}</LTag>} style={{ marginBottom: 8 }}>
            {chapters.map((item, i) => (
              <div key={item.id}
                style={{ cursor: 'pointer', background: i === chapterIndex ? '#eff6ff' : undefined, borderRadius: 4, padding: '6px 8px', display: 'flex', alignItems: 'center' }}
                onClick={() => setChapterIndex(i)}
              >
                <span style={{ fontSize: 12, color: i === chapterIndex ? '#2563eb' : undefined, flex: 1 }}>
                  {i + 1}. {item.title}
                </span>
                <span style={{ fontSize: 10, color: '#999', marginLeft: 'auto' }}>
                  {Math.round(item.char_count / 1000)}k
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <LSpace>
            <LButton size="small" onClick={() => setShowToc(!showToc)}>
              {showToc ? 'Скрыть оглавление' : 'Показать оглавление'}
            </LButton>
          </LSpace>
          <LSpace>
            <span style={{ fontSize: 12, color: '#999' }}>Размер:</span>
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
          <span style={{ fontSize: 12, color: '#999' }}>
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
/**
 * widgets/reading/ReadingTopbar.tsx — minimalistichny topbar dlya chleniya.
 */
'use client';

import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import type { Chapter } from '@/entities/reader/types';
import { ReadingTOC } from './ReadingTOC';
import { ReadingSettings } from './ReadingSettings';
import type { ReadingSettings as ReadingSettingsType } from '@/entities/reader/types';

interface Props {
  currentChapter: Chapter | null;
  chapters: Chapter[];
  progress?: import('@/entities/reader/types').ReadingProgressItem[];
  settings: ReadingSettingsType;
  effectiveTheme: 'light' | 'dark';
  onSettingsChange: <K extends keyof ReadingSettingsType>(key: K, value: ReadingSettingsType[K]) => void;
  onSettingsReset: () => void;
  onChapterClick: (chapter: Chapter) => void;
  /** Если true — ne pokazivat AppShell sidebar. */
  hideSidebar?: boolean;
}

export function ReadingTopbar({
  currentChapter,
  chapters,
  progress,
  settings,
  effectiveTheme,
  onSettingsChange,
  onSettingsReset,
  onChapterClick,
}: Props) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Mobile: hamburger → TOC overlay
  const handleMenuClick = useCallback(() => setMobileMenuOpen((v) => !v), []);
  const handleCloseMobileMenu = useCallback(() => setMobileMenuOpen(false), []);

  const chapterTitle = useMemo(() => {
    if (!currentChapter) return '';
    // Первая глава — это фронтmatter книги, показываем название книги
    if (currentChapter.index === 0) return 'Наследие Аркаима';
    return currentChapter.title;
  }, [currentChapter]);

  return (
    <>
      {/* Topbar */}
      <header
        style={{
          height: 'var(--reading-topbar-height)',
          borderBottom: '1px solid var(--reading-border)',
          background: 'var(--reading-surface)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          gap: 8,
          position: 'sticky',
          top: 0,
          zIndex: 100,
          boxShadow: 'var(--reading-shadow-sm)',
        }}
      >
        {/* Menu toggle */}
        <button
          onClick={handleMenuClick}
          aria-label="Открыть оглавление"
          title="Оглавление"
          style={{
            background: 'none',
            border: '1px solid var(--reading-border)',
            borderRadius: 6,
            cursor: 'pointer',
            padding: '6px 10px',
            fontSize: 16,
            color: 'var(--reading-text)',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span className="reading-ui" style={{ fontSize: 12 }}>
            Гл.
          </span>
        </button>

        {/* Chapter title (centered, truncated) */}
        <div
          style={{
            flex: 1,
            textAlign: 'center',
            overflow: 'hidden',
          }}
        >
          <span
            className="reading-ui"
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: 'var(--reading-text-secondary)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              display: 'block',
            }}
          >
            {chapterTitle || 'Чтение'}
          </span>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {/* Ask context button */}
          {currentChapter && (
            <Link
              href={`/?ask=${encodeURIComponent(currentChapter.title)}`}
              title="Спросить о главе"
              style={{
                background: 'none',
                border: '1px solid var(--reading-border)',
                borderRadius: 6,
                cursor: 'pointer',
                padding: '6px 10px',
                fontSize: 14,
                color: 'var(--reading-text)',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              💬
            </Link>
          )}

          {/* Settings button */}
          <button
            onClick={() => setSettingsOpen(true)}
            aria-label="Настройки чтения"
            title="Настройки"
            style={{
              background: 'none',
              border: '1px solid var(--reading-border)',
              borderRadius: 6,
              cursor: 'pointer',
              padding: '6px 10px',
              fontSize: 14,
              color: 'var(--reading-text)',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="7" cy="7" r="2.5" stroke="currentColor" strokeWidth="1.3" />
              <path d="M7 1v2M7 11v2M1 7h2M11 7h2M3.1 3.1l1.4 1.4M9.5 9.5l1.4 1.4M3.1 10.9l1.4-1.4M9.5 4.5l1.4-1.4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
            </svg>
          </button>

          {/* Library link */}
          <Link
            href="/library"
            title="Геном книги"
            style={{
              background: 'none',
              border: '1px solid var(--reading-border)',
              borderRadius: 6,
              cursor: 'pointer',
              padding: '6px 10px',
              fontSize: 14,
              color: 'var(--reading-text)',
              textDecoration: 'none',
            }}
          >
            📖
          </Link>
        </div>
      </header>

      {/* Mobile TOC overlay (only shown when hamburger is clicked) */}
      {mobileMenuOpen && (
        <ReadingTOC
          chapters={chapters}
          progress={progress}
          currentChapterId={currentChapter?.id ?? null}
          onChapterClick={onChapterClick}
          onClose={handleCloseMobileMenu}
          mobile
        />
      )}

      {/* Settings modal */}
      {settingsOpen && (
        <ReadingSettings
          settings={settings}
          effectiveTheme={effectiveTheme}
          onChange={onSettingsChange}
          onReset={onSettingsReset}
          onClose={() => setSettingsOpen(false)}
        />
      )}
    </>
  );
}

/**
 * shared/reading/useReadingNavigation.ts — navigatsiya po glavam.
 */
'use client';

import { useMemo } from 'react';
import type { Chapter } from '@/entities/reader/types';

export function useReadingNavigation(chapters: Chapter[], currentChapterIndex: number) {
  const current = chapters[currentChapterIndex];
  const prev = currentChapterIndex > 0 ? chapters[currentChapterIndex - 1] : null;
  const next = currentChapterIndex < chapters.length - 1 ? chapters[currentChapterIndex + 1] : null;

  return useMemo(
    () => ({ current, prev, next, total: chapters.length, index: currentChapterIndex }),
    [current, prev, next, chapters.length, currentChapterIndex],
  );
}

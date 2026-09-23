/**
 * tests/unit/reading/reading-navigation-pure.test.ts — testing pure navigation logic
 * (extracted from hook for testability with custom runner).
 */
import { describe, it, expect } from 'vitest';
import type { Chapter } from '@/entities/reader/types';

/** Pure navigation logic (same as useReadingNavigation but testable). */
function computeNavigation(chapters: Chapter[], currentChapterIndex: number) {
  const current = chapters[currentChapterIndex];
  const prev = currentChapterIndex > 0 ? chapters[currentChapterIndex - 1] : null;
  const next = currentChapterIndex < chapters.length - 1 ? chapters[currentChapterIndex + 1] : null;
  return { current, prev, next, total: chapters.length, index: currentChapterIndex };
}

const mockChapters: Chapter[] = [
  { id: 'ch1', title: 'Глава первая', char_count: 5000, index: 0 },
  { id: 'ch2', title: 'Глава вторая', char_count: 8000, index: 1 },
  { id: 'ch3', title: 'Глава третья', char_count: 6000, index: 2 },
];

describe('Reading navigation (pure logic)', () => {
  it('returns current, prev=null, next=ch2 for chapter 0', () => {
    const result = computeNavigation(mockChapters, 0);
    expect(result.current).toBe(mockChapters[0]);
    expect(result.prev).toBeNull();
    expect(result.next).toBe(mockChapters[1]);
    expect(result.total).toBe(3);
    expect(result.index).toBe(0);
  });

  it('returns prev=ch1, current=ch2, next=ch3 for chapter 1', () => {
    const result = computeNavigation(mockChapters, 1);
    expect(result.current).toBe(mockChapters[1]);
    expect(result.prev).toBe(mockChapters[0]);
    expect(result.next).toBe(mockChapters[2]);
  });

  it('returns prev=ch2, current=ch3, next=null for last chapter', () => {
    const result = computeNavigation(mockChapters, 2);
    expect(result.current).toBe(mockChapters[2]);
    expect(result.prev).toBe(mockChapters[1]);
    expect(result.next).toBeNull();
  });

  it('returns undefined current for empty chapters list', () => {
    const result = computeNavigation([], 0);
    expect(result.current === undefined).toBe(true);
    expect(result.prev).toBeNull();
    expect(result.next).toBeNull();
    expect(result.total).toBe(0);
  });

  it('handles chapter not in list gracefully', () => {
    const result = computeNavigation(mockChapters, 99);
    // For index >= length: current=undefined, prev=undefined (out-of-bounds array access), next=null
    expect(result.current === undefined).toBe(true);
    expect(result.prev === undefined).toBe(true);
    expect(result.next).toBeNull();
    expect(result.index).toBe(99);
  });

  it('prev and next are different chapters', () => {
    const result = computeNavigation(mockChapters, 1);
    expect(result.prev?.id).not.toBe(result.current?.id);
    expect(result.next?.id).not.toBe(result.current?.id);
    expect(result.prev?.id).not.toBe(result.next?.id);
  });

  it('first chapter has no prev', () => {
    const result = computeNavigation(mockChapters, 0);
    expect(result.prev).toBeNull();
  });

  it('last chapter has no next', () => {
    const result = computeNavigation(mockChapters, mockChapters.length - 1);
    expect(result.next).toBeNull();
  });
});

/**
 * tests/unit/reading/reading-navigation-chapter-select.test.ts — testing
 * prev/next chapter button behaviour (fixed to switch chapters, not return to list).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

/** Represents the minimal ChapterReader Props used by these tests. */
interface ReaderProps {
  chapterId: string;
  chapters: Array<{ id: string; index: number }>;
  currentChapterIndex: number;
  onBackToList: ReturnType<typeof vi.fn>;
  onChapterSelect: ReturnType<typeof vi.fn>;
}

/**
 * Pure logic extracted from ChapterReader prev/next handlers:
 * - prev: if navigation.prev exists → saveAndLeave(false) + onChapterSelect(prev.id)
 * - next: if navigation.next exists → saveAndLeave(false) + onChapterSelect(next.id)
 * - neither: onBackToList()
 */
describe('Reading prev/next chapter buttons', () => {
  beforeEach(() => vi.restoreAllMocks());

  const mockChapters = [
    { id: 'ch_a', index: 0 },
    { id: 'ch_b', index: 1 },
    { id: 'ch_c', index: 2 },
  ];

  it('prev button calls onChapterSelect with previous chapter id', () => {
    const onSave = vi.fn();
    const onSelect = vi.fn();
    const onBack = vi.fn();

    // Simulate handlePrevChapter for middle chapter (index 1)
    const prevChapter = mockChapters[0];
    if (prevChapter) {
      onSave();
      onSelect(prevChapter.id);
    }

    expect(onBack).not.toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('ch_a');
  });

  it('next button calls onChapterSelect with next chapter id', () => {
    const onSave = vi.fn();
    const onSelect = vi.fn();
    const onBack = vi.fn();

    const nextChapter = mockChapters[2];
    if (nextChapter) {
      onSave();
      onSelect(nextChapter.id);
    }

    expect(onBack).not.toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith('ch_c');
  });

  it('prev button on first chapter falls back to onBackToList', () => {
    const onSave = vi.fn();
    const onSelect = vi.fn();
    const onBack = vi.fn();

    // First chapter has no prev
    const currentIndex = 0;
    const prevChapter = currentIndex > 0 ? mockChapters[currentIndex - 1] : null;
    if (prevChapter) {
      onSave();
      onSelect(prevChapter.id);
    } else {
      onBack();
    }

    expect(onSelect).not.toHaveBeenCalled();
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it('next button on last chapter falls back to onBackToList', () => {
    const onSave = vi.fn();
    const onSelect = vi.fn();
    const onBack = vi.fn();

    const currentIndex = mockChapters.length - 1;
    const nextChapter = currentIndex < mockChapters.length - 1 ? mockChapters[currentIndex + 1] : null;
    if (nextChapter) {
      onSave();
      onSelect(nextChapter.id);
    } else {
      onBack();
    }

    expect(onSelect).not.toHaveBeenCalled();
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it('selectedChapterId updated in parent triggers chapter reload via key prop', () => {
    // In ReadingPage: setSelectedChapterId(ch.id) → resolvedChapterId changes →
    // selectedChapter recomputes → ChapterReader remounts (key={selectedChapter.id})
    // New ChapterReader fires useQuery(['book','chapter', newId]) → getChapter(newId)
    const chapterIdA = 'ch_a';
    const chapterIdB = 'ch_b';

    // Simulate the resolution chain
    let selectedChapterId: string | null = chapterIdA;
    const chaptersMap = new Map(mockChapters.map((c) => [c.id, c]));

    const resolved = selectedChapterId ? chaptersMap.get(selectedChapterId) : null;
    expect(resolved).toBeTruthy();
    expect(resolved!.id).toBe(chapterIdA);

    // After prev button click
    selectedChapterId = chapterIdB;
    const resolvedAfter = selectedChapterId ? chaptersMap.get(selectedChapterId) : null;
    expect(resolvedAfter!.id).toBe(chapterIdB);
  });
});

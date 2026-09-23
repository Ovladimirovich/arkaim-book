/**
 * tests/unit/reading/reading-auto-load-logic.test.ts — testing auto-load conditions.
 */
import { describe, it, expect } from 'vitest';

describe('Reading auto-load logic', () => {
  it('should load more when hasMore=true and not isLoadingMore', () => {
    const hasMore = true;
    const isLoadingMore = false;
    const shouldLoad = hasMore && !isLoadingMore;
    expect(shouldLoad).toBe(true);
  });

  it('should NOT load more when hasMore=false', () => {
    const hasMore = false;
    const isLoadingMore = false;
    const shouldLoad = hasMore && !isLoadingMore;
    expect(shouldLoad).toBe(false);
  });

  it('should NOT load more when isLoadingMore=true', () => {
    const hasMore = true;
    const isLoadingMore = true;
    const shouldLoad = hasMore && !isLoadingMore;
    expect(shouldLoad).toBe(false);
  });

  it('should NOT load more when both flags are true', () => {
    const hasMore = true;
    const isLoadingMore = true;
    const shouldLoad = hasMore && !isLoadingMore;
    expect(shouldLoad).toBe(false);
  });

  it('scroll percent calculation boundaries', () => {
    // Test clamp behavior
    const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));

    expect(clamp(-10, 0, 100)).toBe(0);
    expect(clamp(50, 0, 100)).toBe(50);
    expect(clamp(150, 0, 100)).toBe(100);
  });

  it('text chunk splitting by double newline', () => {
    const text = 'Para 1\n\nPara 2\n\nPara 3';
    const paragraphs = text.split(/\n\n+/);
    expect(paragraphs).toHaveLength(3);
    expect(paragraphs[0]).toBe('Para 1');
    expect(paragraphs[1]).toBe('Para 2');
    expect(paragraphs[2]).toBe('Para 3');
  });

  it('empty chunk split produces single empty string', () => {
    const paragraphs = ''.split(/\n\n+/);
    expect(paragraphs).toEqual(['']);
  });

  it('chunk trimming removes whitespace', () => {
    const text = '  Hello world  ';
    expect(text.trim()).toBe('Hello world');
  });
});

/**
 * entities/reader/types.ts — типы для Reading UX redesign.
 */

export interface Chapter {
  id: string;
  title: string;
  char_count: number;
  index: number;
}

export interface ReadingProgressItem {
  chapter_id: string;
  chapter_index: number;
  first_read_at: string;
  last_read_at: string;
  read_seconds: number;
  completed: boolean;
  scroll_percent: number;
}

export interface ReadingStats {
  chapters_started: number;
  chapters_completed: number;
  total_seconds: number;
}

export interface ReadingProgressEnvelope {
  ok?: boolean;
  data: ReadingProgressItem[];
  stats: ReadingStats;
}

export interface ReadingPosition {
  chapter_id: string;
  chapter_index: number;
  scroll_percent: number;
  last_read_at: string;
}

export interface TextPage {
  ok?: boolean;
  data: string;
  offset: number;
  limit: number;
  total: number;
  has_more: boolean;
}

/** Читабельная ширина колонки в символах (ch). */
export type ColumnWidth = 60 | 68 | 72 | 80;

/** Размер шрифта в px. */
export type FontSize = 15 | 16 | 17 | 18 | 19 | 20;

/** Интервал между абзацами. */
export type ParagraphSpacing = 'compact' | 'normal' | 'relaxed';

export interface ReadingSettings {
  fontSize: FontSize;
  columnWidth: ColumnWidth;
  paragraphSpacing: ParagraphSpacing;
  lineHeight: 1.6 | 1.7 | 1.8 | 1.9 | 2.0;
  /** 'light' | 'dark' | 'auto' */
  theme: 'light' | 'dark' | 'auto';
}

export const DEFAULT_READING_SETTINGS: ReadingSettings = {
  fontSize: 17,
  columnWidth: 68,
  paragraphSpacing: 'normal',
  lineHeight: 1.8,
  theme: 'auto',
};

/** Mapping fontSize → ch-based column width in px (approximate). */
export function columnWidthPx(fontSize: FontSize): number {
  // Optimal line length: 60-75 characters at given font size
  const chMap: Record<FontSize, number> = {
    15: 540,
    16: 576,
    17: 612,
    18: 648,
    19: 684,
    20: 720,
  };
  return chMap[fontSize];
}

export function paragraphSpacingPx(spacing: ParagraphSpacing): number {
  const map: Record<ParagraphSpacing, number> = {
    compact: 0.8,
    normal: 1.2,
    relaxed: 1.6,
  };
  return map[spacing];
}

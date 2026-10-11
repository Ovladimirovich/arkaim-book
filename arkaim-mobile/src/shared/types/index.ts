/**
 * Типы для мобильного приложения.
 * Совпадают с web-приложением.
 */

export type UserRole = 'reader' | 'editor' | 'admin';

export interface User {
  id: string;
  role: UserRole;
  username?: string;
  display_name?: string;
  provider: string;
}

export interface ReaderProfile {
  reader_id: string;
  display_name: string;
  questions_total: number;
  conversation_count: number;
  last_topic: string;
  topics: Array<{ name: string; depth: number; questions: number }>;
}

export interface HistoryItem {
  id: number;
  session_id: string;
  content: string;
  created_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  source?: string;
}

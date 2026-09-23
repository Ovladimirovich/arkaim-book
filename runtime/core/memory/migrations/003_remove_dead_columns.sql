-- 003_remove_dead_columns: Удаление мёртвых колонок
-- Дата: 2026-07-10
-- Проблема: conversations.confidence нигде не используется

PRAGMA foreign_keys = ON;

-- Пересоздать conversations без confidence
CREATE TABLE IF NOT EXISTS conversations_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reader_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    layer_used TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id) ON DELETE CASCADE
);
INSERT OR IGNORE INTO conversations_new (id, reader_id, question, answer, layer_used, created_at)
    SELECT id, reader_id, question, answer, layer_used, created_at FROM conversations;
DROP TABLE IF EXISTS conversations;
ALTER TABLE conversations_new RENAME TO conversations;
CREATE INDEX IF NOT EXISTS idx_conversations_reader ON conversations(reader_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);

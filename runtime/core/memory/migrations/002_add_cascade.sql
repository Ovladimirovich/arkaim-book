-- 002_add_cascade: Добавление ON DELETE CASCADE к внешним ключам readers.db
-- Дата: 2026-07-10
-- Проблема: при удалении читателя orphan-строки в topics/conversations/visual_memory
-- Решение: пересоздать таблицы с CASCADE

PRAGMA foreign_keys = ON;

-- Пересоздать topics с CASCADE
CREATE TABLE IF NOT EXISTS topics_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reader_id TEXT NOT NULL,
    name TEXT NOT NULL,
    depth REAL NOT NULL DEFAULT 0.0,
    questions_count INTEGER NOT NULL DEFAULT 0,
    last_asked TEXT NOT NULL,
    pulse_source TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id) ON DELETE CASCADE
);
INSERT OR IGNORE INTO topics_new SELECT * FROM topics;
DROP TABLE IF EXISTS topics;
ALTER TABLE topics_new RENAME TO topics;
CREATE INDEX IF NOT EXISTS idx_topics_reader ON topics(reader_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_topics_reader_name ON topics(reader_id, name);

-- Пересоздать conversations с CASCADE
CREATE TABLE IF NOT EXISTS conversations_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reader_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    layer_used TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id) ON DELETE CASCADE
);
INSERT OR IGNORE INTO conversations_new SELECT * FROM conversations;
DROP TABLE IF EXISTS conversations;
ALTER TABLE conversations_new RENAME TO conversations;
CREATE INDEX IF NOT EXISTS idx_conversations_reader ON conversations(reader_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);

-- Пересоздать visual_memory с CASCADE
CREATE TABLE IF NOT EXISTS visual_memory_new (
    reader_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    character_id TEXT,
    image_hash TEXT NOT NULL,
    visual_spec_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    cached_until TEXT NOT NULL,
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id) ON DELETE CASCADE
);
INSERT OR IGNORE INTO visual_memory_new SELECT * FROM visual_memory;
DROP TABLE IF EXISTS visual_memory;
ALTER TABLE visual_memory_new RENAME TO visual_memory;
CREATE INDEX IF NOT EXISTS idx_visual_memory_reader ON visual_memory(reader_id);
CREATE INDEX IF NOT EXISTS idx_visual_memory_scene ON visual_memory(scene_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_visual_memory_unique ON visual_memory(reader_id, scene_id, character_id);

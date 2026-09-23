-- Начальная схема для readers.db
-- Создаёт таблицы: readers, topics, conversations

CREATE TABLE IF NOT EXISTS readers (
    reader_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT '',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    questions_total INTEGER NOT NULL DEFAULT 0,
    last_topic TEXT NOT NULL DEFAULT '',
    last_question TEXT NOT NULL DEFAULT '',
    last_answer TEXT NOT NULL DEFAULT '',
    conversation_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reader_id TEXT NOT NULL,
    name TEXT NOT NULL,
    depth REAL NOT NULL DEFAULT 0.0,
    questions_count INTEGER NOT NULL DEFAULT 0,
    last_asked TEXT NOT NULL,
    pulse_source TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id)
);

CREATE INDEX IF NOT EXISTS idx_topics_reader ON topics(reader_id);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reader_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    layer_used TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_reader ON conversations(reader_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);

CREATE TABLE IF NOT EXISTS visual_memory (
    reader_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    character_id TEXT,
    image_hash TEXT NOT NULL,
    visual_spec_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    cached_until TEXT NOT NULL,
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id)
);

CREATE INDEX IF NOT EXISTS idx_visual_memory_reader ON visual_memory(reader_id);
CREATE INDEX IF NOT EXISTS idx_visual_memory_scene ON visual_memory(scene_id);

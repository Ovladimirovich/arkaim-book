-- 001_add_indexes: Добавление недостающих индексов в readers.db
-- Дата: 2026-07-10
-- Проблема: нет композитного уникального индекса на topics, visual_memory без PK

-- Композитный уникальный индекс: один топик на читателя
CREATE UNIQUE INDEX IF NOT EXISTS idx_topics_reader_name ON topics(reader_id, name);

-- Композитный уникальный индекс для visual_memory: предотвращение дубликатов
CREATE UNIQUE INDEX IF NOT EXISTS idx_visual_memory_unique ON visual_memory(reader_id, scene_id, character_id);

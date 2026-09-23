-- 005_add_reading_progress: Таблица прогресса чтения
-- Дата: 2026-07-12
-- Назначение: отслеживание прочитанных глав и восстановление позиции

CREATE TABLE IF NOT EXISTS reading_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reader_id TEXT NOT NULL,
    chapter_id TEXT NOT NULL,
    chapter_index INTEGER NOT NULL,
    first_read_at TEXT NOT NULL,
    last_read_at TEXT NOT NULL,
    read_seconds INTEGER NOT NULL DEFAULT 0,
    completed INTEGER NOT NULL DEFAULT 0,
    scroll_percent REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (reader_id) REFERENCES readers(reader_id) ON DELETE CASCADE,
    UNIQUE(reader_id, chapter_id)
);

CREATE INDEX IF NOT EXISTS idx_reading_progress_reader ON reading_progress(reader_id);

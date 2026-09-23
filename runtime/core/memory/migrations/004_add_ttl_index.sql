-- 004_add_ttl_index: Индекс для быстрой очистки старых диалогов
-- Дата: 2026-07-10
-- Назначение: ускорить DELETE WHERE created_at < threshold

-- Составной индекс для запросов очистки по дате + читателю
CREATE INDEX IF NOT EXISTS idx_conversations_ttl ON conversations(created_at, reader_id);

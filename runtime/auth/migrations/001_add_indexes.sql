-- 001_add_indexes: Добавление недостающих индексов в auth.db
-- Дата: 2026-07-10
-- Проблема: поиск по token_hash и key_hash = полный скан таблицы

-- Индекс для быстрого поиска сессий по хэшу токена
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);

-- Индекс для быстрого поиска API-ключей по хэшу
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

-- Уникальный индекс для предотвращения дублей имён ключей у одного пользователя
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_user_name ON api_keys(user_id, name) WHERE name IS NOT NULL;

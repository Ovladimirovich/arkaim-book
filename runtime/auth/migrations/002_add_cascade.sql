-- 002_add_cascade: Добавление ON DELETE CASCADE к внешним ключам auth.db
-- Дата: 2026-07-10
-- Проблема: при удалении пользователя orphan-строки в sessions/api_keys остаются
-- Решение: пересоздать таблицы с CASCADE (SQLite не поддерживает ALTER FK)

-- Включить поддержку FK
PRAGMA foreign_keys = ON;

-- Пересоздать sessions с CASCADE
CREATE TABLE IF NOT EXISTS sessions_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
INSERT OR IGNORE INTO sessions_new SELECT * FROM sessions;
DROP TABLE IF EXISTS sessions;
ALTER TABLE sessions_new RENAME TO sessions;
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);

-- Пересоздать api_keys с CASCADE
CREATE TABLE IF NOT EXISTS api_keys_new (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    name TEXT,
    last_used_at TEXT,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
INSERT OR IGNORE INTO api_keys_new SELECT * FROM api_keys;
DROP TABLE IF EXISTS api_keys;
ALTER TABLE api_keys_new RENAME TO api_keys;
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_user_name ON api_keys(user_id, name) WHERE name IS NOT NULL;

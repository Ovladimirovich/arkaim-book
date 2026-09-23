-- Exploration History — история исследований World Explorer
CREATE TABLE IF NOT EXISTS exploration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL,
    epoch TEXT,
    branch_count INTEGER DEFAULT 3,
    hypothesis_id TEXT,
    hypothesis_title TEXT,
    result_json TEXT NOT NULL,
    summary TEXT DEFAULT '',
    overall_score REAL DEFAULT 0.0,
    branch_count_actual INTEGER DEFAULT 0,
    duration_ms REAL DEFAULT 0.0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_exploration_user ON exploration_history (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_exploration_created ON exploration_history (created_at);

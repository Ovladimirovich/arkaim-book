-- Story History table for Narrative Engine
CREATE TABLE IF NOT EXISTS story_history (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    prompt TEXT DEFAULT '',
    constraints TEXT DEFAULT '{}',
    validation TEXT DEFAULT '{}',
    score REAL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index for listing recent stories
CREATE INDEX IF NOT EXISTS idx_story_history_created
    ON story_history(created_at DESC);

-- Index for prompt search
CREATE INDEX IF NOT EXISTS idx_story_history_prompt
    ON story_history(prompt);

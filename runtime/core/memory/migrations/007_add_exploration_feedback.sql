-- Exploration Feedback — обратная связь к ветвям исследований
CREATE TABLE IF NOT EXISTS exploration_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT '',
    exploration_id INTEGER,
    branch_rank INTEGER DEFAULT 0,
    branch_type TEXT DEFAULT '',
    branch_title TEXT DEFAULT '',
    rating INTEGER DEFAULT 0 CHECK (rating >= 1 AND rating <= 5),
    comment TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_user ON exploration_feedback (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_exploration ON exploration_feedback (exploration_id);
CREATE INDEX IF NOT EXISTS idx_feedback_branch ON exploration_feedback (branch_rank, branch_type);

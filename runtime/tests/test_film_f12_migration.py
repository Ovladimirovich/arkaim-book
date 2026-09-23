"""F-12: regression tests for real SQLite schema (not just FakeFilmStore).

Verifies that film_shots.quality column exists and works end-to-end
with a real in-memory SQLite database, covering:
- Schema has quality column
- New shots default to quality='standard'
- PUT-style update of quality persists
- Migration is idempotent (pragma guard)
"""
import pytest
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent.parent / "core" / "CORE"
sys.path.insert(0, str(CORE_DIR))

from film_studio.store import FilmProjectStore


@pytest.fixture
def tmp_store(tmp_path):
    """Real FilmProjectStore with a temporary SQLite DB."""
    db = tmp_path / "film_f12_test.db"
    store = FilmProjectStore(db_path=db)
    yield store
    # Connection lifecycle managed by test; close if still open
    if store._conn is not None:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.run_until_complete(store.close())
        except RuntimeError:
            pass  # no running loop — fixture cleanup, ignore


@pytest.mark.asyncio
async def test_quality_column_exists_in_real_schema(tmp_store):
    """Schema must include quality column after _init_tables + _migrate_schema."""
    conn = await tmp_store._get_conn()
    cur = await conn.execute("PRAGMA table_info(film_shots)")
    rows = await cur.fetchall()
    cols = {row[1] for row in rows}
    assert "quality" in cols, "film_shots must have quality column (F-12)"


@pytest.mark.asyncio
async def test_create_shot_sets_quality_default(tmp_store):
    """New shots get quality='standard' by default via INSERT."""
    shot = await tmp_store.create_shot_version(
        scene_id="s_f12_test", project_id="p_f12_test", prompt="test prompt"
    )
    assert shot is not None
    assert shot.quality == "standard", f"Expected 'standard', got {shot.quality!r}"


@pytest.mark.asyncio
async def test_update_shot_quality(tmp_store):
    """PUT-style update of quality must work on real SQLite schema."""
    # Create a shot first
    shot = await tmp_store.create_shot_version(
        scene_id="s_f12_upd", project_id="p_f12_upd", prompt="update test"
    )
    assert shot is not None

    # Update quality
    result = await tmp_store.update_shot(shot.id, quality="ultra")
    assert result is True, "update_shot should return True"

    # Verify persisted value via raw SQL
    conn = await tmp_store._get_conn()
    cur = await conn.execute("SELECT quality FROM film_shots WHERE id=?", (shot.id,))
    row = await cur.fetchone()
    assert row is not None
    assert row[0] == "ultra", f"Expected 'ultra', got {row[0]!r}"


@pytest.mark.asyncio
async def test_migration_idempotent(tmp_store):
    """Running migration logic twice must not fail or duplicate column."""
    conn = await tmp_store._get_conn()
    # First call: should add column (no-op since _get_conn already ran _migrate_schema)
    await tmp_store._migrate_schema()
    # Second call: should be no-op
    await tmp_store._migrate_schema()
    # Verify exactly one quality column
    cur = await conn.execute("PRAGMA table_info(film_shots)")
    rows = await cur.fetchall()
    quality_cols = [r for r in rows if r[1] == "quality"]
    assert len(quality_cols) == 1, f"Expected 1 quality column, got {len(quality_cols)}"


@pytest.mark.asyncio
async def test_existing_rows_get_default_quality():
    """Simulate migration on a DB created without quality column."""
    import aiosqlite
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = Path(f.name)

    try:
        # Create a bare DB with old schema (no quality)
        conn = await aiosqlite.connect(str(tmp_db))
        await conn.execute("""
            CREATE TABLE film_shots (
                id TEXT PRIMARY KEY,
                scene_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                asset_id TEXT,
                prompt TEXT DEFAULT '',
                camera JSON DEFAULT '{}',
                duration_sec REAL DEFAULT 3.0,
                negative_prompt JSON DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                error TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
        """)
        await conn.execute(
            "INSERT INTO film_shots (id, scene_id, project_id, prompt, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            ("sho_legacy", "s1", "p1", "old shot", "pending", "2026-01-01"),
        )
        await conn.commit()
        await conn.close()

        # Now open via FilmProjectStore — should auto-migrate
        store = FilmProjectStore(db_path=tmp_db)
        conn = await store._get_conn()

        # Schema check
        cur = await conn.execute("PRAGMA table_info(film_shots)")
        rows = await cur.fetchall()
        cols = {r[1] for r in rows}
        assert "quality" in cols

        # Data check: legacy row got default
        cur = await conn.execute("SELECT id, quality FROM film_shots")
        row = await cur.fetchone()
        assert row[0] == "sho_legacy"
        assert row[1] == "standard", f"Legacy row should get DEFAULT, got {row[1]!r}"

        await store.close()
    finally:
        tmp_db.unlink(missing_ok=True)

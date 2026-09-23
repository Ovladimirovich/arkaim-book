"""Тесты для core.migration_engine — транзакционные миграции, контрольные суммы."""
import hashlib
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
import aiosqlite

from core.migration_engine import MigrationEngine


@pytest.fixture
def tmp_db_dir(tmp_path):
    """Временная директория для БД и миграций."""
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    return db_dir, migrations_dir


@pytest.fixture
def db_path(tmp_db_dir):
    return tmp_db_dir[0] / "test.db"


@pytest.fixture
def migrations_dir(tmp_db_dir):
    return tmp_db_dir[1]


class TestMigrationEngine:
    @pytest.mark.asyncio
    async def test_run_creates_migrations_table(self, db_path, migrations_dir):
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        executed = await engine.run()
        # _migrations table should exist
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'")
            row = await cursor.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_run_applies_migration(self, db_path, migrations_dir):
        # Create a migration file
        (migrations_dir / "001_create_users.sql").write_text(
            "CREATE TABLE users (id TEXT PRIMARY KEY, name TEXT);"
        )
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        executed = await engine.run()
        assert "001_create_users.sql" in executed

        # Verify table exists
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            assert await cursor.fetchone() is not None

    @pytest.mark.asyncio
    async def test_run_skips_already_applied(self, db_path, migrations_dir):
        (migrations_dir / "001_test.sql").write_text("CREATE TABLE t1 (id TEXT);")
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        await engine.run()
        # Run again
        executed = await engine.run()
        assert len(executed) == 0

    @pytest.mark.asyncio
    async def test_run_multiple_migrations_in_order(self, db_path, migrations_dir):
        (migrations_dir / "002_b.sql").write_text("CREATE TABLE b (id TEXT);")
        (migrations_dir / "001_a.sql").write_text("CREATE TABLE a (id TEXT);")
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        executed = await engine.run()
        assert executed == ["001_a.sql", "002_b.sql"]

    @pytest.mark.asyncio
    async def test_run_transactional_rollback_on_error(self, db_path, migrations_dir):
        # First migration succeeds
        (migrations_dir / "001_ok.sql").write_text("CREATE TABLE ok_table (id TEXT);")
        # Second migration has syntax error
        (migrations_dir / "002_fail.sql").write_text("CREATE TABLE ; INVALID SYNTAX")
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        with pytest.raises(Exception):
            await engine.run()

        # First migration should be applied, second should not
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ok_table'")
            assert await cursor.fetchone() is not None
            cursor = await db.execute("SELECT name FROM _migrations WHERE name='002_fail.sql'")
            assert await cursor.fetchone() is None

    @pytest.mark.asyncio
    async def test_checksum_verification(self, db_path, migrations_dir):
        (migrations_dir / "001_versioned.sql").write_text("CREATE TABLE v1 (id TEXT);")
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        await engine.run()

        # Get status — should show checksum_ok=True
        status = await engine.get_status()
        assert len(status) == 1
        assert status[0]["checksum_ok"] is True

        # Modify the migration file
        (migrations_dir / "001_versioned.sql").write_text("CREATE TABLE v1_modified (id TEXT);")
        status = await engine.get_status()
        assert status[0]["checksum_ok"] is False

    @pytest.mark.asyncio
    async def test_get_status_empty_dir(self, db_path, migrations_dir):
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        status = await engine.get_status()
        assert status == []

    @pytest.mark.asyncio
    async def test_empty_migrations_dir(self, db_path, migrations_dir):
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        executed = await engine.run()
        assert executed == []


class TestMigrationSplitStatements:
    def test_split_simple(self):
        sql = "CREATE TABLE a (id TEXT); CREATE TABLE b (id TEXT);"
        stmts = MigrationEngine._split_statements(sql)
        assert len(stmts) == 2

    def test_split_with_strings(self):
        sql = "INSERT INTO t VALUES ('hello; world'); SELECT 1;"
        stmts = MigrationEngine._split_statements(sql)
        assert len(stmts) == 2
        assert "hello; world" in stmts[0]

    def test_split_skips_comments(self):
        sql = "-- comment\nCREATE TABLE a (id TEXT);"
        stmts = MigrationEngine._split_statements(sql)
        assert len(stmts) == 1

    def test_split_no_trailing_semicolon(self):
        sql = "CREATE TABLE a (id TEXT)"
        stmts = MigrationEngine._split_statements(sql)
        assert len(stmts) == 1

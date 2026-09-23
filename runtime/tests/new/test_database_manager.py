"""Тесты для core.database — DatabaseManager, соединения, WAL mode."""
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
import aiosqlite

from core.database import DatabaseManager


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


class TestDatabaseManager:
    @pytest.mark.asyncio
    async def test_get_connection_creates_file(self, tmp_dir):
        db_path = tmp_dir / "test.db"
        manager = DatabaseManager()
        conn = await manager.get_connection(db_path)
        assert conn is not None
        assert db_path.exists()
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_get_connection_reuses(self, tmp_dir):
        db_path = tmp_dir / "reuse.db"
        manager = DatabaseManager()
        conn1 = await manager.get_connection(db_path)
        conn2 = await manager.get_connection(db_path)
        assert conn1 is conn2
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_connection_has_wal_mode(self, tmp_dir):
        db_path = tmp_dir / "wal.db"
        manager = DatabaseManager()
        conn = await manager.get_connection(db_path)
        cursor = await conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row[0] == "wal"
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_connection_has_foreign_keys_on(self, tmp_dir):
        db_path = tmp_dir / "fk.db"
        manager = DatabaseManager()
        conn = await manager.get_connection(db_path)
        cursor = await conn.execute("PRAGMA foreign_keys")
        row = await cursor.fetchone()
        assert row[0] == 1
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_close_all(self, tmp_dir):
        db1 = tmp_dir / "a.db"
        db2 = tmp_dir / "b.db"
        manager = DatabaseManager()
        await manager.get_connection(db1)
        await manager.get_connection(db2)
        status = manager.get_status()
        assert len(status) == 2
        await manager.close_all()
        status = manager.get_status()
        assert len(status) == 0

    @pytest.mark.asyncio
    async def test_get_status(self, tmp_dir):
        manager = DatabaseManager()
        await manager.get_connection(tmp_dir / "s.db")
        status = manager.get_status()
        assert str(tmp_dir / "s.db") in status
        assert status[str(tmp_dir / "s.db")] is True
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_different_dbs_independent(self, tmp_dir):
        db1 = tmp_dir / "ind1.db"
        db2 = tmp_dir / "ind2.db"
        manager = DatabaseManager()
        conn1 = await manager.get_connection(db1)
        conn2 = await manager.get_connection(db2)
        await conn1.execute("CREATE TABLE t1 (id TEXT)")
        await conn2.execute("CREATE TABLE t2 (id TEXT)")
        # Each DB has only its own table
        cursor1 = await conn1.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='t1'")
        assert await cursor1.fetchone() is not None
        cursor2 = await conn2.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='t1'")
        assert await cursor2.fetchone() is None
        await manager.close_all()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        from core.database import get_db_manager, close_db_manager
        m1 = get_db_manager()
        m2 = get_db_manager()
        assert m1 is m2
        await close_db_manager()

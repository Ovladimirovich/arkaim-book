"""Тесты для MigrationEngine — применение и проверка миграций."""

from pathlib import Path
import tempfile

import pytest
import pytest_asyncio

from core.migration_engine import MigrationEngine


@pytest_asyncio.fixture
async def migration_env():
    """Создаёт временную БД и директорию с миграциями."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        migrations_dir = Path(tmpdir) / "migrations"
        migrations_dir.mkdir(exist_ok=True)
        yield db_path, migrations_dir


@pytest.mark.asyncio
class TestMigrationEngine:
    async def test_creates_migrations_table(self, migration_env):
        """Проверка создания таблицы _migrations."""
        db_path, migrations_dir = migration_env
        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        await engine.run()

        import aiosqlite
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
            )
            assert await cursor.fetchone() is not None

    async def test_applies_new_migration(self, migration_env):
        """Проверка применения новой миграции."""
        db_path, migrations_dir = migration_env

        # Создаём миграцию
        (migrations_dir / "001_test.sql").write_text(
            "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT);"
        )

        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        executed = await engine.run()
        assert len(executed) == 1
        assert executed[0] == "001_test.sql"

        # Проверяем, что таблица создана
        import aiosqlite
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
            )
            assert await cursor.fetchone() is not None

    async def test_migration_idempotent(self, migration_env):
        """Повторный запуск не применяет миграции повторно."""
        db_path, migrations_dir = migration_env

        (migrations_dir / "001_test.sql").write_text(
            "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT);"
        )

        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)

        # Первый запуск
        executed1 = await engine.run()
        assert len(executed1) == 1

        # Второй запуск
        executed2 = await engine.run()
        assert len(executed2) == 0, "Миграции не должны применяться повторно"

    async def test_applies_multiple_migrations_in_order(self, migration_env):
        """Миграции применяются в порядке сортировки по имени."""
        db_path, migrations_dir = migration_env

        (migrations_dir / "002_second.sql").write_text(
            "CREATE TABLE IF NOT EXISTS second_table (id INTEGER PRIMARY KEY);"
        )
        (migrations_dir / "001_first.sql").write_text(
            "CREATE TABLE IF NOT EXISTS first_table (id INTEGER PRIMARY KEY);"
        )

        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        executed = await engine.run()

        assert len(executed) == 2
        assert executed[0] == "001_first.sql", "001 должна быть первой"
        assert executed[1] == "002_second.sql", "002 должна быть второй"

    async def test_get_status(self, migration_env):
        """Проверка статуса миграций."""
        db_path, migrations_dir = migration_env

        (migrations_dir / "001_test.sql").write_text(
            "CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY);"
        )

        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        status = await engine.get_status()
        assert len(status) == 1
        assert status[0]["name"] == "001_test.sql"
        assert status[0]["applied"] is False

        await engine.run()
        status = await engine.get_status()
        assert status[0]["applied"] is True
        assert status[0]["applied_at"] != ""

    async def test_migration_error_logging(self, migration_env):
        """Ошибка в миграции не должна ломать движок."""
        db_path, migrations_dir = migration_env

        (migrations_dir / "001_good.sql").write_text(
            "CREATE TABLE IF NOT EXISTS good_table (id INTEGER PRIMARY KEY);"
        )
        (migrations_dir / "002_bad.sql").write_text(
            "INVALID SQL STATEMENT"
        )
        (migrations_dir / "003_another_good.sql").write_text(
            "CREATE TABLE IF NOT EXISTS another_table (id INTEGER PRIMARY KEY);"
        )

        engine = MigrationEngine(db_path=db_path, migrations_dir=migrations_dir)
        # Должна быть ошибка на 002, и 003 не должна выполниться
        with pytest.raises(Exception, match="(syntax error|near \"INVALID\")"):
            await engine.run()

        # Проверяем, что 001 применилась
        import aiosqlite
        async with aiosqlite.connect(str(db_path)) as db:
            cursor = await db.execute(
                "SELECT name FROM _migrations"
            )
            applied = [row[0] for row in await cursor.fetchall()]
            assert "001_good.sql" in applied
            assert "002_bad.sql" not in applied
            assert "003_another_good.sql" not in applied
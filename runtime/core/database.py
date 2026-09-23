"""
DatabaseManager — единое управление соединениями SQLite.

Один менеджер = одно соединение на каждую БД.
Избавляет каждый Store от собственного connection management.
"""
import logging
from pathlib import Path

import aiosqlite

from core.migration_engine import MigrationEngine

log = logging.getLogger("hermes.database")


class DatabaseManager:
    """Централизованное управление соединениями SQLite."""

    def __init__(self):
        self._connections: dict[str, aiosqlite.Connection] = {}
        self._migration_engines: dict[str, MigrationEngine] = {}

    async def get_connection(
        self,
        db_path: str | Path,
        migrations_dir: str | Path | None = None,
    ) -> aiosqlite.Connection:
        """Получить соединение с БД. Создаёт при первом вызове, переиспользует далее."""
        import logging
        log = logging.getLogger("hermes.database")
        
        key = str(db_path)
        if key in self._connections:
            conn = self._connections[key]
            # Проверяем что соединение активно
            try:
                await conn.execute("SELECT 1")
                return conn
            except Exception as e:
                log.warning("connection_closed_reconnecting key=%s error=%s", key, e)
                # Соединение закрыто — удаляем и создаём новое
                try:
                    del self._connections[key]
                except KeyError:
                    pass

        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        conn = await aiosqlite.connect(key)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")

        self._connections[key] = conn

        # Применяем миграции если указана директория
        if migrations_dir:
            engine = MigrationEngine(db_path=path, migrations_dir=Path(migrations_dir))
            self._migration_engines[key] = engine
            await engine.run(conn)

        log.info("database_connected path=%s", key)
        return conn

    async def close_all(self):
        """Закрыть все соединения."""
        for key, conn in self._connections.items():
            try:
                await conn.close()
                log.info("database_closed path=%s", key)
            except Exception as e:
                log.warning("database_close_error path=%s error=%s", key, e)
        self._connections.clear()
        self._migration_engines.clear()

    def get_status(self) -> dict[str, bool]:
        """Статус соединений."""
        return {key: True for key in self._connections}


# Синглтон — один на всё приложение
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Получить глобальный DatabaseManager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def close_db_manager():
    """Закрыть глобальный DatabaseManager (вызывать при shutdown)."""
    global _db_manager
    if _db_manager is not None:
        await _db_manager.close_all()
        _db_manager = None

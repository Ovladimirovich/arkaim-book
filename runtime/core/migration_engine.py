"""
Движок миграций для SQLite.
- Транзакционные миграции (BEGIN/COMMIT/ROLLBACK)
- Контрольные суммы для обнаружения изменений
- Поддержка внешнего соединения (DatabaseManager)
"""

import hashlib
import logging
from pathlib import Path
from typing import List, Union

import aiosqlite

log = logging.getLogger("hermes.migrations")


class MigrationEngine:
    """Выполняет SQL-миграции в хронологическом порядке."""

    def __init__(self, db_path: Union[str, Path], migrations_dir: Union[str, Path]):
        self.db_path = Path(db_path)
        self.migrations_dir = Path(migrations_dir)

    async def run(self, conn: aiosqlite.Connection | None = None) -> List[str]:
        """Запустить все неприменённые миграции. Возвращает список выполненных."""
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        own_conn = conn is None
        if own_conn:
            conn = await aiosqlite.connect(str(self.db_path))
            conn.row_factory = aiosqlite.Row
            await conn.execute("PRAGMA foreign_keys = ON")

        try:
            # Создаём таблицу учёта миграций (с checksum)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    version INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            await conn.commit()

            # Получаем применённые
            cursor = await conn.execute("SELECT name, checksum FROM _migrations ORDER BY version")
            applied = {row["name"]: row["checksum"] for row in await cursor.fetchall()}

            # Сканируем файлы миграций
            migration_files = sorted(
                self.migrations_dir.glob("*.sql"),
                key=lambda p: int(p.stem.split("_")[0]) if p.stem.split("_")[0].isdigit() else 0,
            )

            executed = []
            for mfile in migration_files:
                sql = mfile.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode()).hexdigest()[:16]

                if mfile.name in applied:
                    # Проверяем не изменился ли файл миграции
                    if applied[mfile.name] != checksum:
                        log.warning(
                            "migration_checksum_mismatch name=%s expected=%s got=%s",
                            mfile.name, applied[mfile.name], checksum,
                        )
                    continue

                # Транзакционное применение
                try:
                    await conn.execute("BEGIN IMMEDIATE")
                    # Разбиваем на отдельные statement (executescript не работает в транзакции)
                    for statement in self._split_statements(sql):
                        if statement.strip():
                            await conn.execute(statement)
                    await conn.execute(
                        "INSERT INTO _migrations (name, checksum) VALUES (?, ?)",
                        (mfile.name, checksum),
                    )
                    await conn.execute("COMMIT")
                    executed.append(mfile.name)
                    log.info("migration_applied name=%s checksum=%s", mfile.name, checksum)
                except Exception as e:
                    await conn.execute("ROLLBACK")
                    log.error("migration_failed name=%s error=%s", mfile.name, e)
                    raise

            return executed
        finally:
            if own_conn:
                await conn.close()

    @staticmethod
    def _split_statements(sql: str) -> list[str]:
        """Разбить SQL на отдельные statements, учитывая ; внутри строк и комментарии."""
        statements = []
        current = []
        in_string = False
        string_char = None

        for char in sql:
            if in_string:
                current.append(char)
                if char == string_char:
                    in_string = False
            else:
                if char in ("'", '"'):
                    in_string = True
                    string_char = char
                    current.append(char)
                elif char == ";":
                    raw = "".join(current).strip()
                    # Убираем строки-комментарии (-- ...)
                    lines = [l for l in raw.splitlines() if not l.strip().startswith("--")]
                    stmt = "\n".join(lines).strip()
                    if stmt:
                        statements.append(stmt)
                    current = []
                else:
                    current.append(char)

        # Последний statement без ;
        stmt = "".join(current).strip()
        if stmt and not stmt.startswith("--"):
            statements.append(stmt)

        return statements

    async def get_status(self) -> List[dict]:
        """Возвращает статус всех миграций."""
        if not self.migrations_dir.exists():
            return []

        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA foreign_keys = ON")
            try:
                cursor = await db.execute(
                    "SELECT name, checksum, applied_at FROM _migrations ORDER BY version"
                )
                applied = {row["name"]: (row["checksum"], row["applied_at"]) for row in await cursor.fetchall()}
            except Exception:
                applied = {}

        migration_files = sorted(
            self.migrations_dir.glob("*.sql"),
            key=lambda p: int(p.stem.split("_")[0]) if p.stem.split("_")[0].isdigit() else 0,
        )

        status = []
        for mfile in migration_files:
            sql = mfile.read_text(encoding="utf-8")
            current_checksum = hashlib.sha256(sql.encode()).hexdigest()[:16]
            entry = applied.get(mfile.name)
            status.append({
                "name": mfile.name,
                "applied": entry is not None,
                "applied_at": entry[1] if entry else "",
                "checksum_ok": entry[0] == current_checksum if entry else False,
            })
        return status

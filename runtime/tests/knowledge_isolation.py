"""Изоляция тестов от рабочей базы знаний.

Тесты полного цикла переиндексации обязаны выполнять «очистка → индексация
книги → индексация сценария», но только во ВРЕМЕННОМ хранилище:
- ChromaDB — в tmp_path/chroma;
- enriched_* (артефакты index_book) — в tmp_path/base/KNOWLEDGE.

Здесь собраны проверки и отпечатки, которые используют и фикстура
`isolated_kernel` (tests/conftest.py), и сами тесты.
"""

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_DIR = REPO_ROOT / "core" / "CORE"


def ensure_core_path() -> None:
    """core/CORE в sys.path — импорт intelligence/config не зависит от порядка тестов."""
    core_path = str(CORE_DIR)
    if core_path not in sys.path:
        sys.path.insert(0, core_path)


def assert_isolated_kernel(kernel, retriever, tmp_path) -> dict:
    """Тестовое ядро обязано работать только во временном хранилище.

    Возвращает фактические пути тестовой базы (их же показываем в отчёте).
    """
    from config import config
    from intelligence import kernel as kernel_module

    tmp = Path(tmp_path).resolve()
    used_chroma = Path(retriever.persist_dir).resolve()
    used_base = Path(kernel_module.BASE).resolve()
    working_chroma = Path(config.CHROMA_DIR).resolve()

    assert kernel.retriever is retriever, "ядро должно работать с переданным временным retriever"
    assert used_chroma != working_chroma, f"тестовый retriever использует рабочую базу: {used_chroma}"
    assert used_chroma.is_relative_to(tmp), f"путь тестовой ChromaDB вне tmp: {used_chroma}"
    assert used_base != CORE_DIR.resolve(), f"тестовый BASE указывает на рабочий каталог: {used_base}"
    assert used_base.is_relative_to(tmp), f"путь тестового BASE вне tmp: {used_base}"
    return {"chroma": str(used_chroma), "knowledge_base": str(used_base)}


def _file_fingerprint(path: Path):
    """Отпечаток файла: размер, mtime_ns, md5 — mtime ловит и равную по содержанию перезапись."""
    if not path.exists():
        return None
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "md5": hashlib.md5(path.read_bytes()).hexdigest(),
    }


def working_knowledge_snapshot(knowledge_dir: Path | None = None, chroma_dir: Path | None = None) -> dict:
    """Отпечаток рабочей базы знаний — только чтение, коллекция не создаётся.

    Пути по умолчанию берутся из config; аргументы нужны, чтобы тест мог
    проверить сам отпечаток на временных данных, не трогая пользовательские.
    """
    ensure_core_path()
    from config import config
    from intelligence.retriever import BookRetriever

    knowledge_dir = Path(knowledge_dir if knowledge_dir is not None else config.KNOWLEDGE_DIR)
    chroma_dir = Path(chroma_dir if chroma_dir is not None else config.CHROMA_DIR)

    snapshot = {
        "enriched_chunks": _file_fingerprint(knowledge_dir / "enriched_chunks.json"),
        "enriched_catalog": _file_fingerprint(knowledge_dir / "enriched_catalog.json"),
        "collection": "absent",
    }

    if not chroma_dir.exists():
        return snapshot

    retriever = BookRetriever(persist_dir=chroma_dir)  # чтение
    client = retriever._get_client()
    if client is None:
        return snapshot
    names = {item if isinstance(item, str) else item.name for item in client.list_collections()}
    if "arkaim_book" not in names:
        return snapshot  # коллекции нет — не создаём, сравнивать нечего

    ids = sorted(retriever._get_collection().get(include=[])["ids"])
    snapshot["collection"] = {
        "count": len(ids),
        "ids_hash": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(),
    }
    return snapshot

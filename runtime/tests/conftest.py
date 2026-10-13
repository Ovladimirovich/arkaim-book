"""Auto-override auth dependency for all tests using core.main.app.

Плюс изоляция тестов от рабочей базы знаний: фикстура `isolated_kernel`
создаёт KnowledgeKernel на временных хранилищах (ChromaDB в tmp,
enriched_* в tmp/base/KNOWLEDGE), а сессионный страж сверяет, что рабочая
база за время прогона не изменилась. Хелперы — в knowledge_isolation.py.
"""

import sys
from pathlib import Path

import pytest
from core.main import app
from auth.rbac import get_current_user
from core.database import close_db_manager

# pytest импортирует conftest раньше, чем кладёт каталог тестов в sys.path.
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from knowledge_isolation import (  # noqa: E402
    assert_isolated_kernel,
    ensure_core_path,
    working_knowledge_snapshot,
)


async def _fake_user():
    return {
        "user_id": "test-user",
        "role": "admin",
        "provider": "test",
        "username": "tester",
        "display_name": "Test User",
    }


app.dependency_overrides[get_current_user] = _fake_user


@pytest.fixture()
def isolated_kernel(tmp_path, monkeypatch):
    """KnowledgeKernel на временных хранилищах — рабочая база знаний не используется.

    reindex_full() сохраняет штатный порядок (очистка → книга → сценарий), но
    очищает и наполняет tmp/chroma, а enriched_* пишет в tmp/base/KNOWLEDGE.

    cwd не подкладывается: путь к сценарию обязан находиться независимо от
    текущей папки (CI переиндексирует из core/, pytest — из runtime/).
    """
    pytest.importorskip("chromadb")
    ensure_core_path()
    from intelligence import kernel as kernel_module
    from intelligence.kernel import KnowledgeKernel
    from intelligence.retriever import BookRetriever

    base = tmp_path / "base"
    (base / "KNOWLEDGE").mkdir(parents=True)
    monkeypatch.setattr(kernel_module, "BASE", base)

    retriever = BookRetriever(persist_dir=tmp_path / "chroma")
    kernel = KnowledgeKernel(retriever=retriever)
    assert_isolated_kernel(kernel, retriever, tmp_path)
    return kernel, retriever


@pytest.fixture(scope="session", autouse=True)
def _guard_working_knowledge_db():
    """Контроль всей сессии: тесты не очищают и не перестраивают рабочую базу."""
    try:
        before = working_knowledge_snapshot()
    except Exception as exc:  # окружение не даёт отпечаток — контроль отключаем
        print(f"[guard] рабочая база недоступна, контроль изоляции отключён: {exc}")
        yield
        return

    yield

    after = working_knowledge_snapshot()
    if before["collection"] == "absent":
        # Свежая копия: чтение может завести пустую коллекцию — сверяем только файлы.
        before = {key: value for key, value in before.items() if key != "collection"}
        after = {key: value for key, value in after.items() if key != "collection"}
    assert after == before, f"тесты изменили рабочую базу знаний (до: {before}, после: {after})"


@pytest.fixture(scope="session", autouse=True)
async def _close_db_manager_at_session_end():
    """Закрыть все соединения aiosqlite после завершения тестовой сессии.

    aiosqlite создаёт не-daemon поток _connection_worker_thread на каждое
    соединение. Если соединения не закрыты, процесс pytest не завершается.
    """
    yield
    await close_db_manager()

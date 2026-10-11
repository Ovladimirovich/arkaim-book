"""Architecture contract tests."""

import importlib
import sys

_PROJECT_PREFIXES = ("gateway", "core", "memory", "observability", "integrations", "skills", "contracts", "cli")
_EXTRA_MODULES = ("aiosqlite",)
_KEEP_MODULES = {"observability.metrics"}


def _is_project_module(name: str) -> bool:
    return name.startswith(_PROJECT_PREFIXES) or name in _EXTRA_MODULES


def _snapshot_modules() -> dict:
    return {m: mod for m, mod in sys.modules.items() if _is_project_module(m)}


def _restore_modules(snapshot: dict) -> None:
    """Вернуть sys.modules к состоянию до пурга (глобальное состояние сессии pytest)."""
    for m in list(sys.modules):
        if _is_project_module(m) and m not in snapshot:
            del sys.modules[m]
    sys.modules.update(snapshot)


def _module_imports_forbidden(modname: str, forbidden_prefix: str) -> bool:
    snapshot = _snapshot_modules()
    try:
        for m in list(sys.modules):
            if _is_project_module(m) and m not in _KEEP_MODULES:
                del sys.modules[m]
        importlib.invalidate_caches()
        try:
            importlib.import_module(modname)
        except ModuleNotFoundError:
            return False
        for m in sys.modules:
            if m.startswith(forbidden_prefix):
                return True
        return False
    finally:
        _restore_modules(snapshot)


class TestContract:
    def test_gateway_no_providers(self):
        assert not _module_imports_forbidden("gateway.main", "core.providers"), "Gateway must not import providers"

    def test_gateway_no_memory(self):
        assert not _module_imports_forbidden("gateway.main", "memory"), "Gateway must not import memory"

    def test_core_no_gateway(self):
        assert not _module_imports_forbidden("core.main", "gateway"), "Core must not import gateway"

    def test_core_no_integrations(self):
        assert not _module_imports_forbidden("core.main", "integrations"), "Core must not import integrations"

    def test_telegram_no_core(self):
        assert not _module_imports_forbidden("integrations.telegram.run", "core"), "Telegram must not import core"

    def test_telegram_no_providers(self):
        assert not _module_imports_forbidden("integrations.telegram.run", "core.providers"), "Telegram must not import providers"


class TestModuleIdentityRestored:
    """_module_imports_forbidden не должен менять идентичность core*-модулей.

    Пург без восстановления оставлял в сессии второй core.main (новый app
    без auth-overrides) и вторые routes-модули, из-за чего последующие
    тесты падали с 401 и ошибками чужой film-БД.
    """

    def test_forbidden_check_restores_module_identity(self):
        before = _snapshot_modules()
        assert "core.main" in before, "conftest must have imported core.main"

        _module_imports_forbidden("gateway.main", "core")

        after = _snapshot_modules()
        assert set(after) == set(before)
        for name, module in before.items():
            assert after[name] is module, f"sys.modules[{name!r}] was replaced by a re-imported module"

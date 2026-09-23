"""Architecture contract tests."""

import importlib
import sys

_PROJECT_PREFIXES = ("gateway", "core", "memory", "observability", "integrations", "skills", "contracts", "cli")
_EXTRA_MODULES = ("aiosqlite",)
_KEEP_MODULES = {"observability.metrics"}


def _module_imports_forbidden(modname: str, forbidden_prefix: str) -> bool:
    for m in list(sys.modules):
        if (m.startswith(_PROJECT_PREFIXES) or m in _EXTRA_MODULES) and m not in _KEEP_MODULES:
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

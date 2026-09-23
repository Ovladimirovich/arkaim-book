"""Gateway architecture tests: gateway must be stateless and dumb."""

from pathlib import Path

from tests.test_contract import _module_imports_forbidden


def _gateway_src_has(modname: str) -> bool:
    root = Path(__file__).resolve().parent.parent
    for py in (root / "gateway").rglob("*.py"):
        if py.name.startswith("__"):
            continue
        text = py.read_text(encoding="utf-8")
        if f"import {modname}" in text or f"from {modname}" in text:
            return True
    return False


class TestGatewayImports:
    def test_gateway_does_not_import_core_orchestrator(self):
        assert not _module_imports_forbidden("gateway.main", "core.orchestrator")

    def test_gateway_does_not_import_providers(self):
        assert not _module_imports_forbidden("gateway.main", "core.providers")

    def test_gateway_has_no_memory_logic(self):
        assert not _gateway_src_has("aiosqlite"), "Gateway source must not import aiosqlite"
        assert not _gateway_src_has("memory"), "Gateway source must not import memory module"
